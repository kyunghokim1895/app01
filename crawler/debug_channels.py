import os
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")
youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

channels = {
    "Main MK Invest": "UCnfwIKyFYRuqZzzKBDt6JOA",
    "Wall Street Sub": "UCIipmgxpUxDmPP-ma3Ahvbw"
}

for name, cid in channels.items():
    print(f"\n--- Checking {name} ({cid}) ---")
    request = youtube.search().list(
        part="snippet",
        channelId=cid,
        maxResults=5,
        order="date",
        publishedAfter="2026-02-19T00:00:00Z",
        type="video"
    )
    response = request.execute()
    items = response.get("items", [])
    print(f"Total found for today/yesterday: {len(items)}")
    for item in items:
        print(f" - {item['snippet']['title']} ({item['id']['videoId']})")
