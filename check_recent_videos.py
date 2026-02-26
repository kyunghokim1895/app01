import os
import json
from dotenv import load_dotenv
from src.core import youtube_service

def main():
    load_dotenv()
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    
    config_path = "src/configs/apps.json"
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    print(f"{'App Name':<20} | {'Video ID':<15} | {'Latest Video Title':<40} | {'Date'}")
    print("-" * 100)
    
    for app in config['apps']:
        try:
            videos = youtube_service.get_video_list(youtube_api_key, app['channel_id'], days=2, max_results=3)
            if videos:
                v = videos[0]
                print(f"{app['name']:<20} | {v['id']:<15} | {v['title'][:40]:<40} | {v['publishedAt']}")
            else:
                print(f"{app['name']:<20} | {'N/A':<15} | {'No videos found in last 2 days':<40} | N/A")
        except Exception as e:
            print(f"{app['name']:<20} | Error: {str(e)[:40]:<40} | N/A")

if __name__ == "__main__":
    main()
