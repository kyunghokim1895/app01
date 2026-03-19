import os
import sys
import time
import random
import subprocess
import glob
import re
import html
from datetime import datetime, timedelta
import http.cookiejar
from youtube_transcript_api import YouTubeTranscriptApi
from requests import Session
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
        "--extractor-args", "youtube:player_client=ios,android,mweb;player_skip=web,canvas,web_embedded",
        "--no-check-certificates",
        "--add-header", "Accept-Language: ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    ]
    
    po_token = os.getenv("YOUTUBE_PO_TOKEN")
    if po_token:
        try:
            idx = cmd.index("--extractor-args")
            cmd[idx+1] = cmd[idx+1] + f";po_token={po_token}"
        except ValueError:
            cmd.extend(["--extractor-args", f"youtube:po_token={po_token}"])
        
    cmd.extend(["-o", temp_prefix])
    
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

def get_video_list(api_key, channel_id, days=7, max_results=30):
    """
    유튜브 API의 playlistItems 엔드포인트를 사용하여 최신 영상 목록을 기져옵니다.
    search 대신 playlist(Uploads)를 조회하여 1 quota 단위로 저렴하게 검색합니다.
    """
    videos = []
    
    try:
        from googleapiclient.discovery import build
        youtube = build("youtube", "v3", developerKey=api_key)
        
        # 'Uploads' 플레이리스트 ID는 채널 ID의 두 번째 글자(C)를 (U)로 바꾼 형태입니다.
        uploads_playlist_id = channel_id[:1] + "U" + channel_id[2:]
        print(f"   [API] Fetching videos from playlist {uploads_playlist_id} (Channel: {channel_id})...")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        request = youtube.playlistItems().list(
            part="snippet,contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=max_results
        )
        response = request.execute()
        
        for item in response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            published_str = item["snippet"]["publishedAt"]
            description = item["snippet"]["description"]
            
            # Filter by publish date
            try:
                pub_date = datetime.fromisoformat(published_str.replace('Z', '+00:00'))
                # If timezone is missing assume UTC
                if pub_date.tzinfo is None:
                    cutoff_date = cutoff_date.replace(tzinfo=None)
                elif cutoff_date.tzinfo is None:
                    cutoff_date = cutoff_date.replace(tzinfo=pub_date.tzinfo)
                    
                if pub_date < cutoff_date:
                    continue
            except Exception as e:
                print(f"   [API] Date parse error for {video_id}: {e}")
                continue
                
            videos.append({
                "id": video_id,
                "title": html.unescape(title),
                "description": description,
                "publishedAt": published_str[:10],
                "videoUrl": f"https://www.youtube.com/watch?v={video_id}"
            })
            
        print(f"   [API] Found {len(videos)} recent videos within {days} days.")
    except Exception as e:
        print(f"   [API ERROR] Failed to fetch video list: {str(e)}")
        
    return videos

def get_transcript(video_id):
    max_retries = 2
    for attempt in range(max_retries):
        temp_cookie_path = f"temp_cookies_v2_{video_id}_{attempt}.txt"
        try:
            time.sleep(2 + random.random() * 2)
            
            # 전역 환경변수 쿠키 처리 (GHA용)
            env_cookies = os.getenv("YOUTUBE_COOKIES")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.dirname(os.path.dirname(current_dir))
            
            current_cookies = None
            if env_cookies:
                env_cookies = env_cookies.strip()
                if not env_cookies.startswith("# Netscape"):
                    env_cookies = "# Netscape HTTP Cookie File\n" + env_cookies
                try:
                    with open(temp_cookie_path, "w") as f: f.write(env_cookies)
                    current_cookies = temp_cookie_path
                except Exception: pass
            else:
                possible_cookies = [
                    os.path.join(root_dir, 'cookies.txt'),
                    os.path.join(root_dir, 'www.youtube.com_cookies.txt')
                ]
                current_cookies = next((p for p in possible_cookies if os.path.exists(p)), None)
            
            # YouTubeTranscriptApi 호출 시도
            try:
                session = Session()
                if current_cookies and os.path.exists(current_cookies):
                    cookie_jar = http.cookiejar.MozillaCookieJar(current_cookies)
                    cookie_jar.load(ignore_discard=True, ignore_expires=True)
                    session.cookies = cookie_jar
                
                # 인스턴스 생성 후 호출 (현재 설치된 버전에 최적화)
                api = YouTubeTranscriptApi(http_client=session)
                transcript_list = api.list(video_id)
                
                try:
                    transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
                except:
                    transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
                
                data = transcript.fetch()
                return " ".join([i.get('text', '') for i in data])
            
            except (TypeError, Exception) as inner_e:
                # 에러 발생 시 기본 인스턴스로 재시도
                if any(x in str(inner_e).lower() for x in ["cookies", "http_client", "unexpected keyword"]):
                    print(f"      [DEBUG] Retrying with basic instance due to API mismatch: {inner_e}")
                    api = YouTubeTranscriptApi()
                    transcript_list = api.list(video_id)
                    transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
                    data = transcript.fetch()
                    return " ".join([i.get('text', '') for i in data])
                raise inner_e

        except Exception as e:
            error_str = str(e).lower()
            if any(x in error_str for x in ["429", "too many requests", "no element found", "unavailable"]):
                print(f"  > [API BLOCKED/UNAVAILABLE] YouTube API issues ({e}). Attempting yt-dlp fallback...")
                fallback_text = get_transcript_via_ytdlp(video_id)
                if fallback_text: return fallback_text
                if "unavailable" not in error_str:
                    time.sleep(15)
            else:
                print(f"  > Transcript Error for {video_id}: {e}")
                # API 실패 시 즉시 yt-dlp 시도
                fallback_text = get_transcript_via_ytdlp(video_id)
                if fallback_text: return fallback_text
                break
        finally:
            if os.path.exists(temp_cookie_path):
                try: os.remove(temp_cookie_path)
                except: pass
    return None
