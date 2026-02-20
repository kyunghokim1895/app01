import os
import googleapiclient.discovery
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")
channel_id = "UCIipmgxpUxDmPP-ma3Ahvbw"

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

# 최근 30일간의 데이터를 확인
thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat() + "Z"

videos = []
next_page_token = None

while True:
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=50,
        order="date",
        publishedAfter=thirty_days_ago,
        pageToken=next_page_token,
        type="video"
    )
    response = request.execute()
    videos.extend(response.get("items", []))
    
    next_page_token = response.get("nextPageToken")
    if not next_page_token:
        break

total_videos = len(videos)
print(f"Total videos in the last 30 days: {total_videos}")
print(f"Average videos per day: {total_videos / 30:.2f}")

# 요일별 분포 확인 (선택적)
counts_by_date = {}
for v in videos:
    date = v['snippet']['publishedAt'][:10]
    counts_by_date[date] = counts_by_date.get(date, 0) + 1

print("\nRecent daily upload counts:")
# 최근 7일만 출력
sorted_dates = sorted(counts_by_date.keys(), reverse=True)
for d in sorted_dates[:7]:
    print(f" - {d}: {counts_by_date[d]} videos")
