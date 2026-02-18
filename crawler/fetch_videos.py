import os
import requests
from datetime import datetime, timedelta

# YouTube API 설정
API_KEY = "YOUR_YOUTUBE_API_KEY"
CHANNEL_ID = "UCpYpD_D_rD_D_rD_D" # 서울경제TV 채널 ID (실제 ID 입력 필요)

def get_videos_last_6_months(api_key, channel_id):
    base_url = "https://www.googleapis.com/youtube/v3/search"
    six_months_ago = (datetime.utcnow() - timedelta(days=180)).isoformat() + "Z"
    
    params = {
        "part": "snippet",
        "channelId": channel_id,
        "maxResults": 50,
        "order": "date",
        "publishedAfter": six_months_ago,
        "type": "video",
        "key": api_key
    }
    
    video_ids = []
    
    while True:
        response = requests.get(base_url, params=params).json()
        
        for item in response.get("items", []):
            video_ids.append({
                "videoId": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "publishedAt": item["snippet"]["publishedAt"]
            })
            
        next_page_token = response.get("nextPageToken")
        if not next_page_token:
            break
        params["pageToken"] = next_page_token
        
    return video_ids

if __name__ == "__main__":
    print(f"Fetching videos from {CHANNEL_ID} for the last 6 months...")
    # 실제 실행 시 API_KEY가 필요합니다.
    # videos = get_videos_last_6_months(API_KEY, CHANNEL_ID)
    # print(f"Found {len(videos)} videos.")
