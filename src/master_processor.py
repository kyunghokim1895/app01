import os
import sys
import json
import time
import random
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Add the project root to sys.path to allow importing from src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import youtube_service, gemini_service, data_manager

def process_app(app_config, model, youtube_api_key):
    """앱 하나를 처리하고 (신규 처리 수, 확인 영상 수) 튜플을 반환합니다."""
    name = app_config['name']
    channel_id = app_config['channel_id']
    json_path = os.path.join(os.getcwd(), app_config['json_path'])
    db_path = os.path.join(os.getcwd(), app_config['db_path'])
    
    print(f"\n>>> Processing App: {name}")
    new_count = 0
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
            # Stage 2: Try Multimodal (Video Download)
            print(f"      No transcript. Trying Stage 2: Multimodal (Video Analysis)...")
            analysis = gemini_service.summarize_from_video(model, video_id)
            
        if not analysis:
            # Stage 3 (Final Resort): Summarize from Metadata (No download needed!)
            print(f"      Stage 2 failed. Final Resort: Summarizing from RSS Metadata...")
            analysis = gemini_service.summarize_from_metadata(model, v['title'], v.get('description', ''))
            
        if not analysis or not analysis.get('summary'):
            print(f"      => CRITICAL: Failed to get even metadata summary for {video_id}")
            continue
            
        # 5. Save to DB and JSON (Incremental)
        data_manager.save_video_to_db(db_path, video_id, v['title'], analysis, v['publishedAt'], v['videoUrl'])
        
        new_item = {
            "id": video_id, "title": v['title'], "summary": analysis['summary'],
            "summaryList": analysis['summaryList'], "keywords": analysis['keywords'],
            "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl'],
            "crawledAt": datetime.now().isoformat()
        }
        data_manager.update_incremental_json(json_path, new_item)
        
        new_count += 1
        print(f"      Successfully updated {video_id}")
        time.sleep(5)
    
    return new_count, len(videos)

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

    success_count = 0
    fail_count = 0
    failed_apps = []
    app_results = []

    for app_config in apps_to_process:
        try:
            new_count, checked_count = process_app(app_config, model, youtube_api_key)
            success_count += 1
            app_results.append({
                "app": app_config['name'],
                "videos_checked": checked_count,
                "new_processed": new_count,
                "status": "success"
            })
        except Exception as e:
            print(f"!!! Error processing {app_config['name']}: {str(e)}")
            fail_count += 1
            failed_apps.append(app_config['name'])
            app_results.append({
                "app": app_config['name'],
                "videos_checked": 0,
                "new_processed": 0,
                "status": f"failed: {str(e)[:100]}"
            })

    # 상세 Summary 출력
    print(f"\n{'='*40}")
    print(f"Update Summary:")
    print(f"  Total Apps: {len(apps_to_process)}")
    for r in app_results:
        print(f"  {r['app']}: {r['videos_checked']}개 확인 → {r['new_processed']}개 신규 처리 [{r['status']}]")
    print(f"  Success: {success_count} / Failure: {fail_count}")
    if failed_apps:
        print(f"  Failed Apps: {', '.join(failed_apps)}")
    print(f"{'='*40}")

    # JSON 리포트 저장
    report = {
        "run_date": datetime.now().isoformat(),
        "total_apps": len(apps_to_process),
        "results": app_results,
        "success": success_count,
        "failure": fail_count
    }
    reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, f"update_report_{datetime.now().strftime('%Y-%m-%d')}.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\nReport saved to {report_path}")

    if fail_count > 0 and success_count == 0:
        print("CRITICAL: All apps failed to process.")
        sys.exit(1)

if __name__ == "__main__":
    main()
