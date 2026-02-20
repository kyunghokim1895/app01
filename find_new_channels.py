import os
import googleapiclient.discovery
from dotenv import load_dotenv

load_dotenv('crawler/.env')
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

def get_channel_id(handle):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=YOUTUBE_API_KEY)
    request = youtube.search().list(
        q=handle,
        type="channel",
        part="id,snippet",
        maxResults=1
    )
    response = request.execute()
    for item in response.get("items", []):
        print(f"Name: {item['snippet']['title']}")
        print(f"Channel ID: {item['id']['channelId']}")
        print("-" * 20)

if __name__ == "__main__":
    handles = ["@hkglobalmarket", "@hk_koreamarket", "@jipconomy"]
    for handle in handles:
        get_channel_id(handle)
