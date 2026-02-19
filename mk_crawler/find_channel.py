import os
from dotenv import load_dotenv
import googleapiclient.discovery
import json

load_dotenv()
api_key = os.getenv("YOUTUBE_API_KEY")

if not api_key:
    print("Error: YOUTUBE_API_KEY not found in .env")
    exit(1)

youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)

# Search for the channel by handle
request = youtube.search().list(
    part="snippet",
    q="@MK_Invest",
    type="channel",
    maxResults=1
)
response = request.execute()

if response.get('items'):
    item = response['items'][0]
    print(f"Found Channel: {item['snippet']['title']}")
    print(f"Channel ID: {item['snippet']['channelId']}")
else:
    print("Channel not found via search. Trying 'forHandle' if available or manual URL check.")
