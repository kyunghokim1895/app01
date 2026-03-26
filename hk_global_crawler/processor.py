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
            videoUrl TEXT,
            category TEXT DEFAULT ''
        )
    ''')
    try:
        cursor.execute("ALTER TABLE videos ADD COLUMN category TEXT DEFAULT ''")
    except:
        pass
    conn.commit()
    conn.close()

def main():
    init_db()

    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: existing_data = json.load(f)
        except: pass

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, summaryList, keywords, publishedAt, videoUrl, COALESCE(category, '') FROM videos WHERE summary IS NOT NULL AND summary != ''")
    db_rows = cursor.fetchall()

    db_data = []
    for row in db_rows:
        try:
            db_data.append({
                "id": row[0], "title": row[1], "summary": row[2],
                "summaryList": json.loads(row[3]), "keywords": json.loads(row[4]),
                "publishedAt": row[5], "videoUrl": row[6], "category": row[7]
            })
        except: pass

    all_data = db_data + existing_data
    unique_data = {item['id']: item for item in all_data}
    sorted_data = sorted(unique_data.values(), key=lambda x: x.get('publishedAt', ''), reverse=True)

    # 안전장치: 데이터 감소 방지
    if existing_data and len(sorted_data) < len(existing_data) * 0.9:
        print(f"  > [SAFETY] 데이터 감소 감지! 기존 {len(existing_data)}개 → {len(sorted_data)}개. 저장을 거부합니다.")
        return

    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)

    existing_data = list(unique_data.values())
    existing_ids = {item['id'] for item in existing_data}

    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID, skip_filter=True)

    for i, v in enumerate(videos):
        cursor.execute("SELECT summary FROM videos WHERE id=?", (v['id'],))
        row = cursor.fetchone()
        if (row and row[0] and len(row[0].strip()) > 0) or v['id'] in existing_ids:
            continue

        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")

        analysis = analysis_service.summarize_from_metadata(
            v['title'], v.get('description', ''), CHANNEL_NAME
        )

        if not analysis or not analysis.get('summary') or len(analysis['summary'].strip()) < 10:
            print(f"   => Failed to get valid summary for {v['id']}")
            continue

        cursor.execute("REPLACE INTO videos VALUES (?,?,?,?,?,?,?,?)", (
            v['id'], v['title'], analysis['summary'],
            json.dumps(analysis['summaryList'], ensure_ascii=False),
            json.dumps(analysis['keywords'], ensure_ascii=False),
            v['publishedAt'], v['videoUrl'], analysis.get('category', '')
        ))
        conn.commit()

        new_item = {
            "id": v['id'], "title": v['title'], "summary": analysis['summary'],
            "summaryList": analysis['summaryList'], "keywords": analysis['keywords'],
            "category": analysis.get('category', ''),
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
