import os
import sys
import sqlite3
import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
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


RETENTION_DAYS = 14

# 중복 필터링용 키워드 목록 (같은 날 같은 주제 영상은 1개만 수집)
DEDUP_KEYWORDS = [
    '삼성전자', 'SK하이닉스', '하이닉스', '엔비디아', '테슬라', '애플', 'TSMC',
    '네이버', '카카오', '현대차', '기아', 'LG엔솔', 'LG에너지', '한화에어로',
    '한화오션', '한화시스템', '포스코', '셀트리온', 'KB금융', '신한지주',
    '메타', '마이크로소프트', '구글', '아마존', '엔비디아',
    '비트코인', '이더리움', '리플', 'XRP', '솔라나', '코인',
    '트럼프', '바이든', '윤석열', '이재명',
    '금값', '유가', '환율', '금리', '국채',
    '반도체', '원전', '조선', '배터리', '방산', '바이오', '로봇', '자율주행',
    '부동산', '전세', '아파트', '분양', '재건축',
]

def dedup_videos_by_topic(videos):
    """같은 날짜에 같은 주제를 다루는 영상은 1개만 남깁니다."""
    def extract_topics(title):
        topics = set()
        for kw in DEDUP_KEYWORDS:
            if kw in title:
                # 유사 키워드 통합
                if kw in ('하이닉스',): topics.add('SK하이닉스')
                elif kw in ('XRP',): topics.add('리플')
                elif kw in ('LG에너지',): topics.add('LG엔솔')
                else: topics.add(kw)
        return frozenset(topics) if topics else None

    seen = set()
    result = []
    for v in videos:
        topics = extract_topics(v['title'])
        if topics is None:
            # 키워드 매칭 안 되는 영상은 모두 포함
            result.append(v)
            continue
        key = (v['publishedAt'], topics)
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result

def save_data(json_path, data_dict):
    """데이터 저장 (보관기간 제한 + 감소 방지 안전장치 포함)"""
    # 보관기간 필터링
    cutoff = (datetime.now() - timedelta(days=RETENTION_DAYS)).strftime('%Y-%m-%d')
    filtered_dict = {k: v for k, v in data_dict.items() if v.get('publishedAt', '')[:10] >= cutoff}
    removed = len(data_dict) - len(filtered_dict)
    if removed > 0:
        print(f"  > [RETENTION] {RETENTION_DAYS}일 초과 항목 {removed}개 제거")

    # 안전장치: 같은 보관기간 기준으로 비교
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                old_data = json.load(f)
            old_filtered_count = sum(1 for item in old_data if item.get('publishedAt', '')[:10] >= cutoff)
            if len(filtered_dict) < old_filtered_count * 0.9:
                print(f"  > [SAFETY] 데이터 감소 감지! 기존 {old_filtered_count}개 → {len(filtered_dict)}개. 저장을 거부합니다.")
                return False
        except Exception:
            pass

    data_list = sorted(filtered_dict.values(), key=lambda x: x.get('publishedAt', ''), reverse=True)
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

    # 3. 같은 날 같은 주제 중복 제거
    before_count = len(videos)
    videos = dedup_videos_by_topic(videos)
    print(f"  > [DEDUP] {before_count} → {len(videos)} videos (removed {before_count - len(videos)} duplicates)")

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
