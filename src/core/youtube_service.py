import os
import sys
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
        sys.executable, "-m", "yt_dlp",
        "--skip-download",
        "--write-auto-subs",
        "--write-subs",
        "--sub-lang", "ko",
        "--js-runtimes", "node",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "--extractor-args", "youtube:player-client=tv,android;player_skip=web,canvas,web_embedded",
        "--no-check-certificates",
        "--add-header", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
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

import urllib.request
import xml.etree.ElementTree as ET

import ssl

def get_video_list(api_key, channel_id, days=3, max_results=10):
    """
    유튜브 API 대신 RSS 피드를 사용하여 최신 영상 목록을 가져옵니다.
    할당량(Quota)을 소모하지 않으며 차단 위험이 낮습니다.
    """
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    videos = []
    
    try:
        print(f"   [RSS] Fetching feed from {rss_url}...")
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = urllib.request.Request(rss_url, headers=headers)
        
        # SSL 인증서 문제 우회 (특히 macOS 로컬 환경 대응)
        context = ssl._create_unverified_context()
        
        with urllib.request.urlopen(req, context=context, timeout=20) as response:
            xml_content = response.read()
            root = ET.fromstring(xml_content)
            
            # Atom Namespace
            ns = {'ns': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
            
            for entry in root.findall('ns:entry', ns):
                v_id_elem = entry.find('yt:videoId', ns)
                title_elem = entry.find('ns:title', ns)
                pub_elem = entry.find('ns:published', ns)
                
                if v_id_elem is None or title_elem is None or pub_elem is None:
                    continue
                    
                video_id = v_id_elem.text
                title = title_elem.text
                published = pub_elem.text
                
                if not video_id or not title or not published:
                    continue
                
                # 날짜 필터링
                try:
                    pub_date = datetime.fromisoformat(published.replace('Z', '+00:00'))
                    if pub_date < datetime.now(pub_date.tzinfo) - timedelta(days=days):
                        continue
                except Exception:
                    continue
                
                videos.append({
                    "id": video_id,
                    "title": html.unescape(title),
                    "publishedAt": published[:10],
                    "videoUrl": f"https://www.youtube.com/watch?v={video_id}"
                })
                
                if len(videos) >= max_results:
                    break
                    
        print(f"   [RSS] Found {len(videos)} recent videos.")
    except Exception as e:
        print(f"   [RSS ERROR] Failed to parse RSS feed: {str(e)}")
        # Fallback to empty list or you could keep old API logic as a very last resort
        # For now, let's rely on RSS as primary for redesign.
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
            if "429" in str(e) or "too many requests" in str(e).lower() or "no element found" in str(e).lower():
                fallback_text = get_transcript_via_ytdlp(video_id)
                if fallback_text: return fallback_text
                time.sleep(15)
            else: break
        finally:
            if os.path.exists(temp_cookie_path) and os.getenv("YOUTUBE_COOKIES"):
                try: os.remove(temp_cookie_path)
                except: pass
    return None
