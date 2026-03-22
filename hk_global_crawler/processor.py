import os
import sys
import sqlite3
import json
import time
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.youtube_service import get_video_list
from src.core.analysis_service import AnalysisService

# .env 파일 로드
load_dotenv()

# === 설정 ===
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "UCWskYkV4c4S9D__rsfOl2JA" # 한경 글로벌마켓
CHANNEL_NAME = "한경 글로벌마켓"

# 서비스 초기화
analysis_service = AnalysisService(GEMINI_API_KEY)

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../HKGlobalApp/src/services/data.json"

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

def main():
    init_db()

    # 1. 기존 JSON 데이터 로드
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: existing_data = json.load(f)
        except: pass

    # 2. DB에서 모든 데이터 읽어서 JSON과 동기화
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

    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

    existing_data = list(unique_data)
    existing_ids = {item['id'] for item in existing_data}

    # 3. 신규 비디오 확인 및 처리
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)

    for i, v in enumerate(videos):
        cursor.execute("SELECT summary FROM videos WHERE id=?", (v['id'],))
        row = cursor.fetchone()
        if (row and row[0] and len(row[0].strip()) > 0) or v['id'] in existing_ids:
            continue

        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")

        # 제목+설명 기반 Gemini 분석
        analysis = analysis_service.summarize_from_metadata(
            v['title'], v.get('description', ''), CHANNEL_NAME
        )

        if not analysis or not analysis.get('summary') or len(analysis['summary'].strip()) < 10:
            print(f"   => Failed to get valid summary for {v['id']}")
            continue

        cursor.execute("REPLACE INTO videos VALUES (?,?,?,?,?,?,?)", (
            v['id'], v['title'], analysis['summary'],
            json.dumps(analysis['summaryList'], ensure_ascii=False),
            json.dumps(analysis['keywords'], ensure_ascii=False),
            v['publishedAt'], v['videoUrl']
        ))
        conn.commit()

        # 실시간 JSON 업데이트
        new_item = {
            "id": v['id'], "title": v['title'], "summary": analysis['summary'],
            "summaryList": analysis['summaryList'], "keywords": analysis['keywords'],
            "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl']
        }

        current_data = []
        if os.path.exists(JSON_OUTPUT_PATH):
            try:
                with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: current_data = json.load(f)
            except: pass

        all_data = [new_item] + current_data
        unique_data = {item['id']: item for item in all_data}.values()
        sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)

        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)

        print(f"      Successfully saved and updated JSON for {v['id']}")
        time.sleep(5)

    conn.close()
    print("Done!")

if __name__ == "__main__":
    main()
