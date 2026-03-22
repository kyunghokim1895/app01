import os
import sys
import sqlite3
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.core.youtube_service import get_video_list
from src.core.analysis_service import AnalysisService

# .env 파일 로드
load_dotenv()

# === 설정 ===
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "UC3p-0EWA8OXko2EUDUXAy5w" # 서울경제TV 공식 채널 ID
CHANNEL_NAME = "서울경제TV"

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
            videoUrl TEXT,
            category TEXT DEFAULT ''
        )
    ''')
    # 기존 DB에 category 컬럼이 없을 경우 추가
    try:
        cursor.execute("ALTER TABLE videos ADD COLUMN category TEXT DEFAULT ''")
    except:
        pass
    conn.commit()
    conn.close()

def main():
    init_db()

    # 1. 기존 JSON 데이터 로드
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"  > 로컬 JSON에서 {len(existing_data)}개의 기존 데이터를 불러왔습니다.")
        except Exception as e:
            print(f"  > JSON 로드 중 오류: {e}")

    existing_ids = {item['id'] for item in existing_data}

    # 2. 영상 목록 가져오기
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    print(f"  > [DEBUG] YouTube API returned total {len(videos)} videos.")

    if not videos:
        print("  > [WARNING] No videos found. Check Channel ID or API Key.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    new_entries = []

    for i, v in enumerate(videos):
        cursor.execute("SELECT id FROM videos WHERE id=?", (v['id'],))
        if cursor.fetchone() or v['id'] in existing_ids:
            continue

        print(f"[{i+1}/{len(videos)}] Processing: {v['title']} ({v['id']})")

        analysis = analysis_service.summarize_from_metadata(
            v['title'], v.get('description', ''), CHANNEL_NAME
        )

        if not analysis:
            print(f"  > [ERROR] Summarization failed for {v['id']}")
            continue

        cursor.execute("""
            INSERT INTO videos (id, title, summary, summaryList, keywords, publishedAt, videoUrl, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            v['id'], v['title'],
            analysis.get("summary", ""),
            json.dumps(analysis.get("summaryList", []), ensure_ascii=False),
            json.dumps(analysis.get("keywords", []), ensure_ascii=False),
            v['publishedAt'], v['videoUrl'],
            analysis.get("category", "")
        ))
        conn.commit()

        new_entries.append({
            "id": v['id'],
            "title": v['title'],
            "summary": analysis.get("summary", ""),
            "summaryList": analysis.get("summaryList", []),
            "keywords": analysis.get("keywords", []),
            "category": analysis.get("category", ""),
            "publishedAt": v['publishedAt'],
            "videoUrl": v['videoUrl']
        })

        time.sleep(5)

    conn.close()

    final_data = new_entries + existing_data

    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Saved {len(final_data)} entries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
