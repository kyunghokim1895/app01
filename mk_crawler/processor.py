import os
import sys
import sqlite3
import json
import random
from datetime import datetime, timedelta
import time
import subprocess
import re
import glob
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import googleapiclient.discovery
from dotenv import load_dotenv

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.youtube_service import get_video_list
from src.core.analysis_service import AnalysisService

# .env 파일 로드
load_dotenv()

# === 설정 ===
# .env 파일에 저장된 키를 가져옵니다.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "UCIipmgxpUxDmPP-ma3Ahvbw" # 매경 월가월부 (@MK_WorldStreet) 전용 채널 ID

# 서비스 초기화
analysis_service = AnalysisService(GEMINI_API_KEY)

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../MKSummaryApp/src/services/data.json"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            summaryList TEXT,
            keywords TEXT,
            publishedAt TEXT,
            videoUrl TEXT
        )
    ''')
    conn.commit()
    conn.close()

import html

# --- 중복 로직 삭제됨 (AnalysisService로 통합) ---


def main():
    init_db()
    
    # 1. 기존 JSON 데이터 로드 (메모리 역할)
    # GitHub Action 환경은 DB파일이 초기화되므로 JSON을 기본 저장소로 활용합니다.
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"  > 로컬 JSON에서 {len(existing_data)}개의 기존 데이터를 불러왔습니다.")
        except Exception as e:
            print(f"  > JSON 로드 중 오류: {e}")
            
    existing_ids = {item['id'] for item in existing_data}

    # 2. 영상 목록 가져오기 (2026년 이후 전수 조사)
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    print(f"  > [DEBUG] YouTube API returned total {len(videos)} videos.")
    
    if not videos:
        print("  > [WARNING] No videos found. Check Channel ID or API Key.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_entries = []
    
    for i, v in enumerate(videos):
        # 3. DB 또는 기존 JSON에 있는지 확인
        cursor.execute("SELECT id FROM videos WHERE id=?", (v['id'],))
        if cursor.fetchone() or v['id'] in existing_ids:
            continue
            
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']} ({v['id']})")
        
        # 유튜브 부하 분산을 위한 대기 시간 대폭 증가 (성공률 위주)
        time.sleep(10 + random.random() * 10)
            
        # 자막 추출 시도
        transcript = analysis_service.get_transcript(v['id'])
        
        if transcript:
            print(f"  > [OK] Transcript found (Length: {len(transcript)}). Summarizing...")
            analysis = analysis_service.summarize_with_gemini(transcript, "매경 월가월부")
        else:
            # 최종 수단: 직접 듣기
            analysis = analysis_service.summarize_from_audio(v['id'])
            
        if not analysis:
            print(f"  > [ERROR] All summarization methods failed for {v['id']}")
            continue
            
        # DB에 즉시 저장 (중간에 멈춰도 데이터 보존)
        cursor.execute("""
            INSERT INTO videos (id, title, summary, summaryList, keywords, publishedAt, videoUrl)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            v['id'], 
            v['title'], 
            analysis.get("summary", ""), 
            json.dumps(analysis.get("summaryList", []), ensure_ascii=False),
            json.dumps(analysis.get("keywords", []), ensure_ascii=False),
            v['publishedAt'],
            v['videoUrl']
        ))
        conn.commit()
        
        entry = {
            "id": v['id'],
            "title": v['title'],
            "summary": analysis.get("summary", ""),
            "summaryList": analysis.get("summaryList", []),
            "keywords": analysis.get("keywords", []),
            "publishedAt": v['publishedAt'],
            "videoUrl": v['videoUrl']
        }
        
        new_entries.append(entry)
        time.sleep(5) # Gemini Free Tier RPM(15) 준수를 위해 넉넉히 대기
        
    conn.close()
    
    # 4. 결과 병합 (새로운 것 + 기존 것)
    # get_video_list가 최신순으로 가져오므로 new_entries를 앞에 둠
    final_data = new_entries + existing_data
    
    # [FALLBACK] 만약 데이터가 하나도 없으면 (크롤링 실패 시) 더미 데이터 생성
    if not final_data:
        print("  > 크롤링 실패 또는 데이터 없음. 더미 데이터를 생성합니다.")
        final_data = [
            {
                "id": "dummy_1",
                "title": "엔비디아 실적 발표, AI 반도체 시장의 미래는?",
                "summary": "엔비디아의 2분기 실적이 시장 예상치를 상회하며 AI 반도체 수요가 여전히 강력함을 입증했습니다. 데이터센터 매출이 급증하며 주가 상승을 견인하고 있습니다.",
                "summaryList": [
                    "1. 엔비디아 분기 매출이 사상 최대치를 기록하며 AI 붐이 지속되고 있음을 증명했습니다.",
                    "2. 데이터센터 부문 매출이 전년 대비 3배 이상 증가하며 성장을 주도했습니다.",
                    "3. 젠슨 황 CEO는 가속 컴퓨팅과 생성형 AI가 티핑 포인트에 도달했다고 언급했습니다.",
                    "4. 월가는 목표 주가를 잇달아 상향 조정하며 향후 전망을 긍정적으로 평가했습니다.",
                    "5. 다만 공급망 제약 문제가 여전히 리스크 요인으로 지적되고 있습니다."
                ],
                "keywords": ["#엔비디아", "#AI반도체", "#미국주식", "#실적발표"],
                "publishedAt": datetime.now().strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example1"
            },
            {
                "id": "dummy_2",
                "title": "미국 연준 금리 인하 시기, 월가의 예측은?",
                "summary": "미국 연준의 금리 인하 시점에 대한 월가의 전망이 엇갈리고 있습니다. 물가 지표가 둔화되고 있지만, 연준은 여전히 신중한 입장을 고수하고 있어 9월 인하설이 힘을 얻고 있습니다.",
                "summaryList": [
                    "1. 최근 발표된 CPI 지수가 예상보다 낮게 나오며 인플레이션 둔화 신호를 보였습니다.",
                    "2. 파월 의장은 금리 인하에 대한 확신을 갖기 위해 더 많은 데이터가 필요하다고 강조했습니다.",
                    "3. 골드만삭스와 JP모건은 9월 첫 금리 인하가 단행될 것으로 전망하고 있습니다.",
                    "4. 고용 시장의 냉각 조짐이 금리 인하 압박을 키우고 있다는 분석입니다.",
                    "5. 시장은 연내 2회 금리 인하 가능성을 가격에 반영하고 있습니다."
                ],
                "keywords": ["#연준", "#금리인하", "#미국경제", "#월가전망"],
                "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example2"
            },
            {
                "id": "dummy_3",
                "title": "테슬라 로봇택시 공개, 주가에 미칠 영향",
                "summary": "테슬라가 다가오는 8월 8일 로봇택시를 공개할 예정입니다. 자율주행 기술의 완성도와 상용화 가능성에 시장의 이목이 집중되고 있으며, 이는 테슬라 주가의 새로운 모멘텀이 될 전망입니다.",
                "summaryList": [
                    "1. 일론 머스크는 8월 8일 로봇택시 공개를 예고하며 자율주행 사업에 대한 자신감을 드러냈습니다.",
                    "2. FSD(Full Self-Driving) 기술의 발전이 로봇택시 상용화의 핵심 열쇠가 될 것입니다.",
                    "3. 저가형 모델(모델 2) 개발 지연 우려 속에 로봇택시가 새로운 성장 동력이 될지 주목됩니다.",
                    "4. 규제 당국의 승인 여부와 사고 책임 문제가 여전히 해결해야 할 과제로 남아있습니다.",
                    "5. 캐시 우드는 테슬라의 로봇택시 사업 가치를 높게 평가하며 목표 주가를 상향했습니다."
                ],
                "keywords": ["#테슬라", "#로봇택시", "#자율주행", "#일론머스크"],
                "publishedAt": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example3"
            }
        ]
    
    # JSON 출력 (앱에서 사용)
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone! Saved {len(final_data)} summaries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
