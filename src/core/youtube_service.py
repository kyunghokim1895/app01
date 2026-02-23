import os
import time
import random
import subprocess
import glob
import re
import html
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
import googleapiclient.discovery

def clean_vtt(vtt_text):
    lines = vtt_text.splitlines()
    clean_lines = []
    for line in lines:
        if "-->" in line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        line = re.sub(r'<[^>]+>', '', line)
        line = line.strip()
        if line:
            clean_lines.append(line)
    final_lines = []
    for line in clean_lines:
        if not final_lines or final_lines[-1] != line:
            final_lines.append(line)
    return " ".join(final_lines)

def get_transcript_via_ytdlp(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    temp_prefix = f"temp_sub_{video_id}"
    cmd = [
        "python3", "-m", "yt_dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "ko",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-o", temp_prefix,
    ]
    
    # Try multiple cookie locations relative to current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    possible_cookies = [
        os.path.join(root_dir, 'cookies.txt'),
        os.path.join(root_dir, 'www.youtube.com_cookies.txt')
    ]
    cookie_file = next((p for p in possible_cookies if os.path.exists(p)), None)
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    cmd.append(url)
    
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        files = glob.glob(f"{temp_prefix}*")
        sub_file = next((f for f in files if f.endswith(('.vtt', '.srt'))), None)
        if sub_file:
            with open(sub_file, 'r', encoding='utf-8') as f:
                content = f.read()
            for f in files: os.remove(f)
            return clean_vtt(content) if sub_file.endswith('.vtt') else content
    except Exception:
        for f in glob.glob(f"{temp_prefix}*"): os.remove(f)
    return None

def get_video_list(api_key, channel_id, days=30, max_results=30):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    videos = []
    next_page_token = None
    while True:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=50,
            order="date",
            publishedAfter=published_after,
            pageToken=next_page_token,
            type="video"
        )
        response = request.execute()
        items = response.get("items", [])
        for item in items:
            videos.append({
                "id": item["id"]["videoId"],
                "title": html.unescape(item["snippet"]["title"]),
                "publishedAt": item["snippet"]["publishedAt"][:10],
                "videoUrl": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
        next_page_token = response.get("nextPageToken")
        if not next_page_token or len(videos) >= max_results: break
    return videos

def get_transcript(video_id):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            env_cookies = os.getenv("YOUTUBE_COOKIES")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            temp_cookie_path = os.path.join(root_dir, "temp_cookies_v2.txt")
            
            if env_cookies:
                with open(temp_cookie_path, "w") as f: f.write(env_cookies)
                cookies = temp_cookie_path
            else:
                possible_cookies = [
                    os.path.join(root_dir, 'cookies.txt'),
                    os.path.join(root_dir, 'www.youtube.com_cookies.txt')
                ]
                cookies = next((p for p in possible_cookies if os.path.exists(p)), None)
            
            time.sleep(2 + random.random() * 2)
            if cookies:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
            else:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            try:
                transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
            except:
                transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
            
            data = transcript.fetch()
            return " ".join([i.get('text', '') for i in data])
        except Exception as e:
            if "429" in str(e) or "too many requests" in str(e).lower():
                fallback_text = get_transcript_via_ytdlp(video_id)
                if fallback_text: return fallback_text
                time.sleep(15)
            else: break
        finally:
            if os.path.exists(temp_cookie_path) and os.getenv("YOUTUBE_COOKIES"):
                try: os.remove(temp_cookie_path)
                except: pass
    return None
