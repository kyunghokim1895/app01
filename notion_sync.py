#!/usr/bin/env python3
"""
유튜브 영상 아카이브 → Notion 동기화 (채널별 DB)

각 크롤러가 생성한 data.json을 읽어, 채널마다 대응하는 Notion DB에 영상별로
한 페이지씩 기록한다. 영상ID 기준으로 멱등(idempotent)하게 동작하여 이미 올라간
영상은 다시 만들지 않는다.

구조:
  Notion "📺 유튜브 영상 아카이브" 페이지 하위에 채널별 DB 6개.
  각 DB 속성: 제목/카테고리/키워드/게시일/요약/링크/영상ID/동기화, 본문에 summaryList.

동기화 정책:
  - 서울경제TV: SENTV_CUTOFF 이후 게시된 영상만 (과거 대량 백필 방지)
  - 나머지 5개 채널: 전체 영상

중복 방지:
  실행 시작 시 각 DB를 페이지네이션하여 이미 기록된 "영상ID" 집합을 수집하고,
  그 집합에 없는 영상만 새로 생성한다. (로컬 상태파일 불필요)

DB ID 주입:
  기본값은 아래 DB_MAP에 하드코딩(토큰 없이는 무의미하므로 비밀 아님). 필요 시
  환경변수 NOTION_DATABASE_MAP(JSON: {채널명: db_id})로 덮어쓸 수 있다.
"""
import os
import sys
import json
import time
import requests
from datetime import date
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

# 서울경제TV는 14일 보관정책으로 data.json이 롤링 윈도우(약 1,500건)다. 전체 백필을
# 막기 위해 이 날짜(포함) 이후 게시분만 기록한다. 최초 도입(2026-05-27) 시 최근 3일치
# (2026-05-25~27)를 시드로 넣고, 이후 새 영상은 자동으로 함께 동기화된다(영상ID 중복 제거).
SENTV_CUTOFF = "2026-05-25"

# 채널별 Notion DB ID (📺 유튜브 영상 아카이브 페이지 하위)
DB_MAP = {
    "서울경제TV":       "36da3330-1343-814e-9387-f4ac559d44d8",
    "매경 월가월부":     "36da3330-1343-81e5-a294-ea7e0fe6f2bc",
    "한경 글로벌마켓":   "36da3330-1343-819b-9aa3-d4ecb86f8e4e",
    "한경 코리아마켓":   "36da3330-1343-81ab-912b-eb6506ada0cc",
    "집코노미TV":        "36da3330-1343-81bd-94be-e8da3fc9ba76",
    "한국경제TV 글로벌": "36da3330-1343-818a-958c-c09146cfa00e",
}
# 환경변수로 덮어쓰기 (선택)
_env_map = os.getenv("NOTION_DATABASE_MAP", "").strip()
if _env_map:
    try:
        DB_MAP.update(json.loads(_env_map))
    except json.JSONDecodeError:
        print("⚠️ NOTION_DATABASE_MAP JSON 파싱 실패 — 기본 DB_MAP 사용")

# (data.json 경로, 채널 표시명, 모드)  모드: "all" | "new_only"
CHANNELS = [
    ("SentvSummaryApp/src/services/data.json", "서울경제TV",      "new_only"),
    ("MKSummaryApp/src/services/data.json",    "매경 월가월부",    "all"),
    ("HKGlobalApp/src/services/data.json",     "한경 글로벌마켓",  "all"),
    ("HKKoreaApp/src/services/data.json",      "한경 코리아마켓",  "all"),
    ("JipconomyApp/src/services/data.json",    "집코노미TV",       "all"),
    ("HKTVGlobalApp/src/services/data.json",   "한국경제TV 글로벌", "all"),
]

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}


def _rt(text):
    """rich_text / title 용 — Notion 2000자 제한 대응."""
    return [{"type": "text", "text": {"content": (text or "")[:2000]}}]


def fetch_existing_video_ids(db_id):
    """해당 DB를 전부 순회하여 이미 기록된 영상ID 집합을 반환."""
    ids = set()
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(f"{API}/databases/{db_id}/query",
                          headers=HEADERS, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        for page in data.get("results", []):
            for t in page.get("properties", {}).get("영상ID", {}).get("rich_text", []):
                vid = t.get("plain_text", "").strip()
                if vid:
                    ids.add(vid)
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break
    return ids


def build_page(video):
    props = {
        "제목":   {"title": _rt(video.get("title", ""))},
        "게시일": {"date": {"start": video["publishedAt"]}},
        "요약":   {"rich_text": _rt(video.get("summary", ""))},
        "영상ID": {"rich_text": _rt(video["id"])},
        "동기화": {"date": {"start": date.today().isoformat()}},
    }
    if video.get("category"):
        props["카테고리"] = {"select": {"name": video["category"]}}
    if video.get("videoUrl"):
        props["링크"] = {"url": video["videoUrl"]}
    kws = [k.lstrip("#")[:100] for k in video.get("keywords", []) if k.strip()]
    if kws:
        props["키워드"] = {"multi_select": [{"name": k} for k in kws[:10]]}

    children = [
        {"object": "block", "type": "bulleted_list_item",
         "bulleted_list_item": {"rich_text": _rt(line)}}
        for line in video.get("summaryList", []) if line.strip()
    ]
    return props, children


def create_page(video, db_id):
    props, children = build_page(video)
    payload = {"parent": {"database_id": db_id}, "properties": props}
    if children:
        payload["children"] = children[:100]  # Notion children 한도
    r = requests.post(f"{API}/pages", headers=HEADERS, json=payload, timeout=30)
    if r.status_code == 429:  # rate limit
        time.sleep(int(r.headers.get("Retry-After", "2")))
        return create_page(video, db_id)
    r.raise_for_status()
    return r.json()


def select_videos(videos, mode):
    if mode == "new_only":
        return [v for v in videos if v.get("publishedAt", "") >= SENTV_CUTOFF]
    return list(videos)


def main():
    if not NOTION_TOKEN:
        print("❌ NOTION_TOKEN 미설정 (.env 또는 GitHub Secrets 확인)")
        sys.exit(1)

    total_new = 0
    for rel_path, channel, mode in CHANNELS:
        db_id = DB_MAP.get(channel)
        if not db_id:
            print(f"⚠️  {channel}: DB ID 없음 (DB_MAP 확인) — 건너뜀")
            continue
        path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(path):
            print(f"⚠️  {channel}: data.json 없음 ({rel_path}) — 건너뜀")
            continue
        with open(path, encoding="utf-8") as f:
            videos = json.load(f)

        existing = fetch_existing_video_ids(db_id)
        candidates = select_videos(videos, mode)
        to_push = [v for v in candidates if v.get("id") and v["id"] not in existing]
        print(f"📺 {channel}: 전체 {len(videos)} / 대상 {len(candidates)} / 기존 {len(existing)} / 신규 {len(to_push)}")

        pushed = 0
        for v in to_push:
            try:
                create_page(v, db_id)
                pushed += 1
                total_new += 1
                time.sleep(0.34)  # ~3 req/s 속도제한 준수
            except Exception as e:
                print(f"   ⚠️ 실패 ({v.get('id')}): {e}")
        if pushed:
            print(f"   ✅ {pushed}건 기록")

    print(f"\n✅ 동기화 완료 — 신규 {total_new}건")


if __name__ == "__main__":
    main()
