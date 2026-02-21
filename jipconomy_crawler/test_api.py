import os
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")
channel_id = "UCAVdqlngIAxHtwlCA2hjv3A"

try:
    youtube = build("youtube", "v3", developerKey=api_key)
    request = youtube.search().list(
        part="snippet",
        channelId=channel_id,
        maxResults=10,
        order="date",
        type="video"
    )
    response = request.execute()
    for item in response.get("items", []):
        print(f"{item['snippet']['publishedAt']} | {item['snippet']['title']}")
except Exception as e:
    print(f"Error: {e}")
