import os
import re
import time
import html
from datetime import datetime, timedelta
import googleapiclient.discovery

def get_video_list(api_key, channel_id, days=7, max_results=None):
    """
    유튜브 API의 playlistItems 엔드포인트를 사용하여 최신 영상 목록을 가져옵니다.
    페이지네이션으로 기간 내 모든 영상을 수집한 뒤, 쇼츠(60초 이하)와 라이브 방송을 제외합니다.
    """
    max_retries = 3

    for attempt in range(max_retries):
        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

            uploads_playlist_id = channel_id[:1] + "U" + channel_id[2:]
            print(f"   [API] Fetching videos from playlist {uploads_playlist_id} (Channel: {channel_id})...")

            cutoff_date = datetime.now() - timedelta(days=days)

            # 1단계: 페이지네이션으로 기간 내 모든 영상 ID 수집
            candidates = []
            next_page = None
            reached_cutoff = False

            while not reached_cutoff:
                request = youtube.playlistItems().list(
                    part="snippet,contentDetails",
                    playlistId=uploads_playlist_id,
                    maxResults=50,
                    pageToken=next_page
                )
                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["contentDetails"]["videoId"]
                    title = item["snippet"]["title"]
                    published_str = item["snippet"]["publishedAt"]
                    description = item["snippet"]["description"]

                    try:
                        pub_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                        if pub_date.tzinfo is None:
                            cutoff_date = cutoff_date.replace(tzinfo=None)
                        elif cutoff_date.tzinfo is None:
                            cutoff_date = cutoff_date.replace(tzinfo=pub_date.tzinfo)

                        if pub_date < cutoff_date:
                            reached_cutoff = True
                            break
                    except Exception as e:
                        print(f"   [API] Date parse error for {video_id}: {e}")
                        continue

                    candidates.append({
                        "id": video_id,
                        "title": html.unescape(title),
                        "description": description,
                        "publishedAt": published_str[:10],
                        "videoUrl": f"https://www.youtube.com/watch?v={video_id}"
                    })

                next_page = response.get("nextPageToken")
                if not next_page:
                    break

            print(f"   [API] Found {len(candidates)} candidates within {days} days.")

            if not candidates:
                return []

            # 2단계: 쇼츠 및 라이브 필터링
            videos = _filter_shorts_and_lives(youtube, candidates)
            print(f"   [API] After filtering: {len(videos)} videos (excluded {len(candidates) - len(videos)} shorts/lives).")
            return videos

        except Exception as e:
            error_msg = str(e)
            if any(x in error_msg.lower() for x in ["unable to find the server", "gaierror", "nodename nor servname", "dns"]):
                wait_time = (attempt + 1) * 10
                print(f"   [API DNS ERROR] Attempt {attempt+1}/{max_retries} failed: {error_msg}")
                if attempt < max_retries - 1:
                    print(f"   [RETRY] Waiting {wait_time}s before retrying DNS resolution...")
                    time.sleep(wait_time)
                    continue
            else:
                print(f"   [API ERROR] Non-DNS failure: {error_msg}")
                break

    return []


def _filter_shorts_and_lives(youtube, candidates):
    """쇼츠(60초 이하)와 라이브 방송을 제외합니다."""
    video_ids = [v["id"] for v in candidates]
    exclude_ids = set()

    # 50개씩 배치로 조회
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i+50]
        request = youtube.videos().list(
            part="contentDetails,liveStreamingDetails",
            id=",".join(batch)
        )
        response = request.execute()

        for item in response.get("items", []):
            vid = item["id"]
            duration = item["contentDetails"]["duration"]

            # duration 파싱 (초 단위)
            match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if match:
                total_sec = int(match.group(1) or 0) * 3600 + int(match.group(2) or 0) * 60 + int(match.group(3) or 0)
            else:
                total_sec = 0

            is_short = total_sec <= 60
            is_live = "liveStreamingDetails" in item

            if is_short or is_live:
                exclude_ids.add(vid)

    return [v for v in candidates if v["id"] not in exclude_ids]
