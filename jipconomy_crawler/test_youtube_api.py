import os
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env")
api_key = os.getenv("YOUTUBE_API_KEY")
channel_id = "UCAVdqlngIAxHtwlCA2hjv3A" # 집코노미

print(f"Using API Key: {api_key[:5]}...")

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
request = youtube.search().list(
    part="snippet",
    channelId=channel_id,
    maxResults=10,
    order="date",
    type="video"
)
response = request.execute()
for item in response.get("items", []):
    print(f"ID: {item['id']['videoId']}, Title: {item['snippet']['title']}, Date: {item['snippet']['publishedAt']}")
