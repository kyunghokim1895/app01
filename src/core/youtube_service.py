import os
import time
import html
from datetime import datetime, timedelta
import googleapiclient.discovery

def get_video_list(api_key, channel_id, days=7, max_results=30):
    """
    유튜브 API의 playlistItems 엔드포인트를 사용하여 최신 영상 목록을 가져옵니다.
    search 대신 playlist(Uploads)를 조회하여 1 quota 단위로 저렴하게 검색합니다.
    시스템 DNS 오류 대비 재시도 로직(최대 3회)을 포함합니다.
    """
    videos = []
    max_retries = 3

    for attempt in range(max_retries):
        try:
            from googleapiclient.discovery import build
            youtube = build("youtube", "v3", developerKey=api_key, cache_discovery=False)

            uploads_playlist_id = channel_id[:1] + "U" + channel_id[2:]
            print(f"   [API] Fetching videos from playlist {uploads_playlist_id} (Channel: {channel_id})...")

            cutoff_date = datetime.now() - timedelta(days=days)

            request = youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=max_results
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
                        continue
                except Exception as e:
                    print(f"   [API] Date parse error for {video_id}: {e}")
                    continue

                videos.append({
                    "id": video_id,
                    "title": html.unescape(title),
                    "description": description,
                    "publishedAt": published_str[:10],
                    "videoUrl": f"https://www.youtube.com/watch?v={video_id}"
                })

            print(f"   [API] Found {len(videos)} recent videos within {days} days.")
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

    return videos
