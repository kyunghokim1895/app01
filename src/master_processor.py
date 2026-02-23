import os
import sys
import json
import time
import random
import argparse
from dotenv import load_dotenv

# Add the project root to sys.path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import youtube_service, gemini_service, data_manager

def process_app(app_config, model, youtube_api_key):
    name = app_config['name']
    channel_id = app_config['channel_id']
    json_path = os.path.join(os.getcwd(), app_config['json_path'])
    db_path = os.path.join(os.getcwd(), app_config['db_path'])
    
    print(f"\n>>> Processing App: {name}")
    
    # 1. Initialize
    data_manager.init_db(db_path)
    
    # 2. Sync DB to JSON (Startup Sync)
    print(f"   Syncing DB ({db_path}) to JSON ({json_path})...")
    existing_ids = data_manager.sync_db_to_json(db_path, json_path)
    
    # 3. Get Video List
    print(f"   Fetching video list for channel {channel_id}...")
    videos = youtube_service.get_video_list(youtube_api_key, channel_id)
    
    # 4. Process Each Video
    for i, v in enumerate(videos):
        video_id = v['id']
        
        # Check if already processed (exists in JSON or DB with valid summary)
        # We check DB specifically for summary validity
        if video_id in existing_ids:
            continue
            
        print(f"   [{i+1}/{len(videos)}] Processing: {v['title']}")
        
        # Random sleep to mimic human behavior
        time.sleep(10 + random.random() * 10)
        
        transcript = youtube_service.get_transcript(video_id)
        analysis = None
        
        if transcript:
            analysis = gemini_service.summarize_with_gemini(model, transcript)
        
        if not analysis:
            analysis = gemini_service.summarize_from_audio(model, video_id)
            
        if not analysis or not analysis.get('summary') or not isinstance(analysis['summary'], str) or len(analysis['summary'].strip()) < 10:
            print(f"      => Failed to get valid summary for {video_id}")
            continue
            
        # 5. Save to DB and JSON (Incremental)
        data_manager.save_video_to_db(db_path, video_id, v['title'], analysis, v['publishedAt'], v['videoUrl'])
        
        new_item = {
            "id": video_id, "title": v['title'], "summary": analysis['summary'],
            "summaryList": analysis['summaryList'], "keywords": analysis['keywords'],
            "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl']
        }
        data_manager.update_incremental_json(json_path, new_item)
        
        print(f"      Successfully updated {video_id}")
        time.sleep(5)

def main():
    load_dotenv()
    youtube_api_key = os.getenv("YOUTUBE_API_KEY")
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    
    if not youtube_api_key or not gemini_api_key:
        print("Error: API keys not found in .env")
        return

    parser = argparse.ArgumentParser(description="Master Processor for 5 News Apps")
    parser.add_argument("--app", help="Name of the app to process (or 'all')", default="all")
    args = parser.parse_args()

    # Load config
    config_path = os.path.join(os.path.dirname(__file__), "configs", "apps.json")
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # Init Gemini
    model = gemini_service.init_gemini(gemini_api_key)

    apps_to_process = []
    if args.app == "all":
        apps_to_process = config['apps']
    else:
        apps_to_process = [a for a in config['apps'] if a['name'] == args.app]

    if not apps_to_process:
        print(f"Error: No app found with name '{args.app}'")
        return

    for app_config in apps_to_process:
        try:
            process_app(app_config, model, youtube_api_key)
        except Exception as e:
            print(f"Error processing {app_config['name']}: {str(e)}")

if __name__ == "__main__":
    main()
