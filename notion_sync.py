#!/usr/bin/env python3
"""
유튜브 영상 아카이브 → Notion 동기화

각 크롤러가 생성한 data.json을 읽어 Notion DB("유튜브 영상 아카이브")에
영상별로 한 페이지씩 기록한다. 영상ID 기준으로 멱등(idempotent)하게 동작하여
이미 올라간 영상은 다시 만들지 않는다.

동기화 정책:
  - 서울경제TV: SENTV_CUTOFF(오늘 최초 실행일) 이후 게시된 영상만
  - 나머지 5개 채널: 전체 영상

중복 방지:
  실행 시작 시 Notion DB를 전부 페이지네이션하여 이미 기록된 "영상ID" 집합을
  수집하고, 그 집합에 없는 영상만 새로 생성한다. (로컬 상태파일 불필요 — 상태가
  유실돼도 중복이 생기지 않음)
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
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip()
NOTION_VERSION = "2022-06-28"
API = "https://api.notion.com/v1"

# 서울경제TV는 이 날짜(포함) 이후 게시분만 기록. 그 이전 과거 영상은 백필하지 않음.
# 최초 도입 시 최근 3일치(2026-04-28~30, 최신 게시분)를 백필하도록 이 날짜로 설정.
# 이후 크롤러가 더 최신 영상을 추가하면 자동으로 함께 동기화된다(영상ID 중복 제거).
SENTV_CUTOFF = "2026-04-28"

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


def fetch_existing_video_ids():
    """DB를 전부 순회하여 이미 기록된 영상ID 집합을 반환."""
    ids = set()
    cursor = None
    while True:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor
        r = requests.post(f"{API}/databases/{NOTION_DATABASE_ID}/query",
                          headers=HEADERS, json=body, timeout=30)
        r.raise_for_status()
        data = r.json()
        for page in data.get("results", []):
            prop = page.get("properties", {}).get("영상ID", {})
            for t in prop.get("rich_text", []):
                vid = t.get("plain_text", "").strip()
                if vid:
                    ids.add(vid)
        if data.get("has_more"):
            cursor = data.get("next_cursor")
        else:
            break
    return ids


def build_page(video, channel):
    props = {
        "제목":     {"title": _rt(video.get("title", ""))},
        "채널":     {"select": {"name": channel}},
        "게시일":   {"date": {"start": video["publishedAt"]}},
        "요약":     {"rich_text": _rt(video.get("summary", ""))},
        "영상ID":   {"rich_text": _rt(video["id"])},
        "동기화":   {"date": {"start": date.today().isoformat()}},
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


def create_page(video, channel):
    props, children = build_page(video, channel)
    payload = {"parent": {"database_id": NOTION_DATABASE_ID}, "properties": props}
    if children:
        payload["children"] = children[:100]  # Notion children 한도
    r = requests.post(f"{API}/pages", headers=HEADERS, json=payload, timeout=30)
    if r.status_code == 429:  # rate limit
        wait = int(r.headers.get("Retry-After", "2"))
        time.sleep(wait)
        return create_page(video, channel)
    r.raise_for_status()
    return r.json()


def select_videos(videos, mode):
    if mode == "new_only":
        return [v for v in videos if v.get("publishedAt", "") >= SENTV_CUTOFF]
    return list(videos)


def main():
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        print("❌ NOTION_TOKEN 또는 NOTION_DATABASE_ID 미설정 (.env 확인)")
        sys.exit(1)

    print("🔎 기존 기록된 영상ID 수집 중...")
    existing = fetch_existing_video_ids()
    print(f"   기존 {len(existing)}건")

    total_new = 0
    for rel_path, channel, mode in CHANNELS:
        path = os.path.join(BASE_DIR, rel_path)
        if not os.path.exists(path):
            print(f"⚠️  {channel}: data.json 없음 ({rel_path}) — 건너뜀")
            continue
        with open(path, encoding="utf-8") as f:
            videos = json.load(f)
        candidates = select_videos(videos, mode)
        to_push = [v for v in candidates if v.get("id") and v["id"] not in existing]
        print(f"📺 {channel}: 전체 {len(videos)} / 대상 {len(candidates)} / 신규 {len(to_push)}")

        pushed = 0
        for v in to_push:
            try:
                create_page(v, channel)
                existing.add(v["id"])
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
