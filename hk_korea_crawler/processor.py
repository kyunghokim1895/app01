import os
import sqlite3
import json
import random
from datetime import datetime, timedelta
import time
import subprocess
import re
import glob
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import googleapiclient.discovery
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# === 설정 ===
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "UCGCGxsbmG_9nincyI7xypow" # 한경 코리아마켓

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../HKKoreaApp/src/services/data.json"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            summaryList TEXT,
            keywords TEXT,
            publishedAt TEXT,
            videoUrl TEXT
        )
    ''')
    conn.commit()
    conn.close()

import html

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
    possible_cookies = [
        os.path.join(os.path.dirname(__file__), 'cookies.txt'),
        os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')
    ]
    cookie_file = next((p for p in possible_cookies if os.path.exists(p)), None)
    if cookie_file:
        cmd.extend(["--cookies", cookie_file])
    cmd.append(url)
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        files = glob.glob(f"{temp_prefix}*")
        sub_file = next((f for f in files if f.endswith(('.vtt', '.srt'))), None)
        if sub_file:
            with open(sub_file, 'r', encoding='utf-8') as f:
                content = f.read()
            for f in files: os.remove(f)
            return clean_vtt(content) if sub_file.endswith('.vtt') else content
    except Exception as e:
        for f in glob.glob(f"{temp_prefix}*"): os.remove(f)
    return None

def get_video_list(api_key, channel_id):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.now() - timedelta(days=14)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        if not next_page_token or len(videos) >= 5: break
    return videos

def get_transcript(video_id):
    max_retries = 2
    for attempt in range(max_retries):
        try:
            env_cookies = os.getenv("YOUTUBE_COOKIES")
            temp_cookie_path = os.path.join(os.path.dirname(__file__), "temp_cookies.txt")
            if env_cookies:
                with open(temp_cookie_path, "w") as f: f.write(env_cookies)
                cookies = temp_cookie_path
            else:
                possible_cookies = [
                    os.path.join(os.path.dirname(__file__), 'cookies.txt'),
                    os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')
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
                time.sleep(30)
            else: break
        finally:
            if os.path.exists(temp_cookie_path) and os.getenv("YOUTUBE_COOKIES"):
                try: os.remove(temp_cookie_path)
                except: pass
    return None

def parse_json_from_gemini(text_resp):
    try:
        if "```" in text_resp:
            json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_resp, re.DOTALL)
            if json_match: text_resp = json_match.group(1)
            else: text_resp = re.sub(r"```(json)?", "", text_resp).strip()
        result = json.loads(text_resp)
        return {
            "summary": result.get("summary", result.get("요약", "")),
            "summaryList": result.get("summaryList", result.get("요점", result.get("핵심내용", []))),
            "keywords": result.get("keywords", result.get("키워드", []))
        }
    except: return None

def summarize_with_gemini(text):
    prompt = f"다음 영상을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) JSON으로 작성해줘: {text}"
    try:
        response = model.generate_content(prompt)
        return parse_json_from_gemini(response.text)
    except: return None

def summarize_from_audio(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    audio_path = f"temp_audio_{video_id}.m4a"
    cmd = ["python3", "-m", "yt_dlp", "-f", "ba[ext=m4a]", "-o", audio_path, "--max-filesize", "20M", "--js-runtimes", "node", "--remote-components", "ejs:github", url]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=180)
        sample_file = genai.upload_file(path=audio_path, display_name=f"Audio_{video_id}")
        prompt = "오디오 내용을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) JSON으로 작성해줘."
        response = model.generate_content([sample_file, prompt])
        genai.delete_file(sample_file.name)
        os.remove(audio_path)
        return parse_json_from_gemini(response.text)
    except:
        if os.path.exists(audio_path): os.remove(audio_path)
    return None

def main():
    init_db()
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: existing_data = json.load(f)
    existing_ids = {item['id'] for item in existing_data}
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    new_entries = []
    for i, v in enumerate(videos):
        cursor.execute("SELECT id FROM videos WHERE id=?", (v['id'],))
        if cursor.fetchone() or v['id'] in existing_ids: continue
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")
        transcript = get_transcript(v['id'])
        analysis = summarize_with_gemini(transcript) if transcript else summarize_from_audio(v['id'])
        if not analysis: continue
        cursor.execute("INSERT INTO videos VALUES (?,?,?,?,?,?,?)", (v['id'], v['title'], analysis['summary'], json.dumps(analysis['summaryList'], ensure_ascii=False), json.dumps(analysis['keywords'], ensure_ascii=False), v['publishedAt'], v['videoUrl']))
        conn.commit()
        new_entries.append({"id": v['id'], "title": v['title'], "summary": analysis['summary'], "summaryList": analysis['summaryList'], "keywords": analysis['keywords'], "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl']})
        time.sleep(5)
    conn.close()
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f: json.dump(new_entries + existing_data, f, ensure_ascii=False, indent=2)
    print("Done!")

if __name__ == "__main__":
    main()
