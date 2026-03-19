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
CHANNEL_ID = "UCGCGxsbmG_9nincyI7xypow" # 한경 코리아마켓 채널 ID

# 서비스 초기화
analysis_service = AnalysisService(GEMINI_API_KEY)

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../HKKoreaApp/src/services/data.json"

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
    
    # 1. 기존 JSON 데이터 로드
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: existing_data = json.load(f)
        except: pass

    # 2. DB에서 모든 데이터 읽어서 JSON과 동기화 (누락된 것 방지)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, summaryList, keywords, publishedAt, videoUrl FROM videos WHERE summary IS NOT NULL AND summary != ''")
    db_rows = cursor.fetchall()
    
    db_data = []
    for row in db_rows:
        try:
            db_data.append({
                "id": row[0], "title": row[1], "summary": row[2],
                "summaryList": json.loads(row[3]), "keywords": json.loads(row[4]),
                "publishedAt": row[5], "videoUrl": row[6]
            })
        except: pass
        
    # 병합 및 정렬
    all_data = db_data + existing_data
    unique_data = {item['id']: item for item in all_data}.values()
    sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    # 동기화된 데이터 저장
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
    
    existing_data = list(unique_data) # 업데이트된 데이터로 갱신
    existing_ids = {item['id'] for item in existing_data}
    
    # 3. 신규 비디오 확인 및 처리
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    new_entries_count = 0
    
    for i, v in enumerate(videos):
        # 이미 존재하고 요약이 제대로 되어있다면 건너뜀
        cursor.execute("SELECT summary FROM videos WHERE id=?", (v['id'],))
        row = cursor.fetchone()
        if (row and row[0] and len(row[0].strip()) > 0) or v['id'] in existing_ids:
            continue
            
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")
        # 자막 추출 시도
        transcript = analysis_service.get_transcript(v['id'])
        
        if transcript:
            print(f"  > [OK] Transcript found (Length: {len(transcript)}). Summarizing...")
            analysis = analysis_service.summarize_with_gemini(transcript, "서울경제TV")
        else:
            # 최종 수단: 직접 듣기
            analysis = analysis_service.summarize_from_audio(v['id'])
        if not analysis or not analysis.get('summary') or not isinstance(analysis['summary'], str) or len(analysis['summary'].strip()) < 10:
            print(f"   => Failed to get valid summary for {v['id']}")
            continue
            
        cursor.execute("REPLACE INTO videos VALUES (?,?,?,?,?,?,?)", (v['id'], v['title'], analysis['summary'], json.dumps(analysis['summaryList'], ensure_ascii=False), json.dumps(analysis['keywords'], ensure_ascii=False), v['publishedAt'], v['videoUrl']))
        conn.commit()
        
        # 실시간 JSON 업데이트
        new_item = {"id": v['id'], "title": v['title'], "summary": analysis['summary'], "summaryList": analysis['summaryList'], "keywords": analysis['keywords'], "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl']}
        
        current_data = []
        if os.path.exists(JSON_OUTPUT_PATH):
            try:
                with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: current_data = json.load(f)
            except: pass
            
        all_data = [new_item] + current_data
        unique_data = {item['id']: item for item in all_data}.values()
        sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            
        print(f"      Successfully saved and updated JSON for {v['id']}")
        time.sleep(5)
    conn.close()
    
    # 잔여 임시 파일 정리 (.part 파일 등)
    for f in glob.glob("temp_audio_*"):
        try: os.remove(f)
        except: pass
        
    print("Done!")

if __name__ == "__main__":
    main()
