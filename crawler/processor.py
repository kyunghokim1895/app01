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
CHANNEL_ID = "UC3p-0EWA8OXko2EUDUXAy5w" # 서울경제TV 공식 채널 ID

# 서비스 초기화
analysis_service = AnalysisService(GEMINI_API_KEY)

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../SentvSummaryApp/src/services/data.json"

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
        
        # 유튜브 부하 분산을 위한 랜덤 대기 (인간처럼 보이게 함)
        time.sleep(10 + random.random() * 10)
            
        # 자막 추출 시도
        transcript = analysis_service.get_transcript(v['id'])
        
        if transcript:
            print(f"  > [OK] Transcript found (Length: {len(transcript)}). Summarizing...")
            analysis = analysis_service.summarize_with_gemini(transcript, "서울경제TV")
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
    
    # JSON 출력 (앱에서 사용)
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone! Saved {len(final_data)} summaries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
