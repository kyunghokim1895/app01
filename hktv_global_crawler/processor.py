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
CHANNEL_ID = "UC8Q2uQrjoOyUWa8NFYItDWA"  # 한국경제TV 글로벌
CHANNEL_NAME = "한국경제TV 글로벌"

# 서비스 초기화
analysis_service = AnalysisService(GEMINI_API_KEY)

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../HKTVGlobalApp/src/services/data.json"

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

def load_existing_data(json_path):
    """기존 JSON을 ID 기준 dict로 로드 (기존 데이터 보존 보장)"""
    if not os.path.exists(json_path):
        return {}
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"  > 로컬 JSON에서 {len(data)}개의 기존 데이터를 불러왔습니다.")
        return {item['id']: item for item in data}
    except Exception as e:
        print(f"  > JSON 로드 중 오류: {e}")
        return {}


def save_data(json_path, data_dict):
    """데이터 저장 (감소 방지 안전장치 포함)"""
    # 안전장치: 10% 이상 감소 시 저장 거부
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            if len(data_dict) < len(old_data) * 0.9:
                print(f"  > [SAFETY] 데이터 감소 감지! 기존 {len(old_data)}개 → {len(data_dict)}개. 저장을 거부합니다.")
                return False
        except Exception:
            pass

    data_list = sorted(data_dict.values(), key=lambda x: x.get('publishedAt', ''), reverse=True)
    os.makedirs(os.path.dirname(json_path), exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data_list, f, ensure_ascii=False, indent=2)
    return True


def main():
    init_db()

    # 1. 기존 JSON 데이터를 ID 기준 dict로 로드
    existing_dict = load_existing_data(JSON_OUTPUT_PATH)

    # 2. 영상 목록 가져오기
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    print(f"  > [DEBUG] YouTube API returned total {len(videos)} videos.")

    if not videos:
        print("  > [WARNING] No videos found. Check Channel ID or API Key.")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    new_count = 0

    for i, v in enumerate(videos):
        # 기존 JSON 또는 DB에 있으면 건너뛰기
        cursor.execute("SELECT id FROM videos WHERE id=?", (v['id'],))
        if cursor.fetchone() or v['id'] in existing_dict:
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

        # 기존 dict에 신규 항목 추가 (기존 항목은 절대 삭제되지 않음)
        existing_dict[v['id']] = {
            "id": v['id'],
            "title": v['title'],
            "summary": analysis.get("summary", ""),
            "summaryList": analysis.get("summaryList", []),
            "keywords": analysis.get("keywords", []),
            "category": analysis.get("category", ""),
            "publishedAt": v['publishedAt'],
            "videoUrl": v['videoUrl']
        }
        new_count += 1

        time.sleep(5)

    conn.close()

    print(f"  > 신규 {new_count}개 추가. 총 {len(existing_dict)}개.")

    if save_data(JSON_OUTPUT_PATH, existing_dict):
        print(f"\nDone! Saved {len(existing_dict)} entries to {JSON_OUTPUT_PATH}")
    else:
        print(f"\n[ERROR] 저장 실패 - 데이터 감소 방지 안전장치 작동")

if __name__ == "__main__":
    main()
