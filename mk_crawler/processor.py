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
CHANNEL_ID = "UCIipmgxpUxDmPP-ma3Ahvbw" # 매경 월가월부 채널 ID
CHANNEL_NAME = "매경 월가월부"

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
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"  > 로컬 JSON에서 {len(existing_data)}개의 기존 데이터를 불러왔습니다.")
        except Exception as e:
            print(f"  > JSON 로드 중 오류: {e}")

    existing_ids = {item['id'] for item in existing_data}

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

    if not final_data:
        print("  > 크롤링 실패 또는 데이터 없음. 더미 데이터를 생성합니다.")
        final_data = [
            {
                "id": "dummy_1",
                "title": "엔비디아 실적 발표, AI 반도체 시장의 미래는?",
                "summary": "엔비디아의 2분기 실적이 시장 예상치를 상회하며 AI 반도체 수요가 여전히 강력함을 입증했습니다.",
                "summaryList": [
                    "1. 엔비디아 분기 매출이 사상 최대치를 기록했습니다.",
                    "2. 데이터센터 부문 매출이 전년 대비 3배 이상 증가했습니다.",
                    "3. 젠슨 황 CEO는 AI가 티핑 포인트에 도달했다고 언급했습니다.",
                    "4. 월가는 목표 주가를 상향 조정했습니다.",
                    "5. 공급망 제약 문제가 리스크 요인으로 지적됩니다."
                ],
                "keywords": ["#엔비디아", "#AI반도체", "#미국주식", "#실적발표"],
                "category": "해외증시",
                "publishedAt": datetime.now().strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example1"
            }
        ]

    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print(f"\nDone! Saved {len(final_data)} entries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
