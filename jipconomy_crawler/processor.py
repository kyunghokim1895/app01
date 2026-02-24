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
CHANNEL_ID = "UCAVdqlngIAxHtwlCA2hjv3A" # 집코노미

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../JipconomyApp/src/services/data.json"

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
    published_after = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        if not next_page_token or len(videos) >= 30: break
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
            if "429" in str(e) or "too many requests" in str(e).lower() or "no element found" in str(e).lower():
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
    cmd = ["python3", "-m", "yt_dlp", "-f", "ba[ext=m4a]", "-o", audio_path, "--max-filesize", "100M", "--js-runtimes", "node", "--remote-components", "ejs:github", url]
    try:
        print(f"      Downloading audio for {video_id}...")
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        
        if not os.path.exists(audio_path):
            print(f"      Audio file not found after download: {audio_path}")
            return None
            
        print(f"      Uploading to Gemini...")
        sample_file = genai.upload_file(path=audio_path, display_name=f"Audio_{video_id}")
        
        # Wait for file to be ready
        while sample_file.state.name == "PROCESSING":
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)
            
        print(f"      Generating summary...")
        prompt = """오디오 내용을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) 포맷으로 분석해줘.
반드시 아래와 같은 형태의 순수 JSON 객체로만 응답하고, 마크다운(```json 등)이나 다른 설명은 절대 추가하지 마:
{
  "summary": "전체 내용 한글 요약",
  "summaryList": ["핵심 문장 1", "핵심 문장 2", "핵심 문장 3", "핵심 문장 4", "핵심 문장 5"],
  "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
}"""
        response = model.generate_content(
            [sample_file, prompt],
            generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
        )
        
        genai.delete_file(sample_file.name)
        os.remove(audio_path)
        return parse_json_from_gemini(response.text)
    except Exception as e:
        print(f"      Error in summarize_from_audio: {str(e)}")
        if os.path.exists(audio_path): os.remove(audio_path)
    return None

def main():
    init_db()
    
    # 1. 기존 JSON 데이터 로드
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: existing_data = json.load(f)
        except: pass

    # 2. DB에서 모든 데이터 읽어서 JSON과 동기화 (누락된 것 방지)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, summaryList, keywords, publishedAt, videoUrl FROM videos WHERE summary IS NOT NULL AND summary != ''")
    db_rows = cursor.fetchall()
    
    db_data = []
    for row in db_rows:
        try:
            db_data.append({
                "id": row[0], "title": row[1], "summary": row[2],
                "summaryList": json.loads(row[3]), "keywords": json.loads(row[4]),
                "publishedAt": row[5], "videoUrl": row[6]
            })
        except: pass
        
    # 병합 및 정렬
    all_data = db_data + existing_data
    unique_data = {item['id']: item for item in all_data}.values()
    sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    # 동기화된 데이터 저장
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted_data, f, ensure_ascii=False, indent=2)
    
    existing_data = list(unique_data) # 업데이트된 데이터로 갱신
    existing_ids = {item['id'] for item in existing_data}
    
    # 3. 신규 비디오 확인 및 처리
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    new_entries_count = 0
    
    for i, v in enumerate(videos):
        # 이미 존재하고 요약이 제대로 되어있다면 건너뜀
        cursor.execute("SELECT summary FROM videos WHERE id=?", (v['id'],))
        row = cursor.fetchone()
        if (row and row[0] and len(row[0].strip()) > 0) or v['id'] in existing_ids:
            continue
            
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")
        
        # 유튜브 부하 분산을 위한 랜덤 대기 (인간처럼 보이게 함)
        time.sleep(10 + random.random() * 10)
        transcript = get_transcript(v['id'])
        analysis = summarize_with_gemini(transcript) if transcript else summarize_from_audio(v['id'])
        if not analysis or not analysis.get('summary') or not isinstance(analysis['summary'], str) or len(analysis['summary'].strip()) < 10:
            print(f"   => Failed to get valid summary for {v['id']}")
            continue
            
        cursor.execute("REPLACE INTO videos VALUES (?,?,?,?,?,?,?)", (v['id'], v['title'], analysis['summary'], json.dumps(analysis['summaryList'], ensure_ascii=False), json.dumps(analysis['keywords'], ensure_ascii=False), v['publishedAt'], v['videoUrl']))
        conn.commit()
        
        # 실시간 JSON 업데이트
        new_item = {"id": v['id'], "title": v['title'], "summary": analysis['summary'], "summaryList": analysis['summaryList'], "keywords": analysis['keywords'], "publishedAt": v['publishedAt'], "videoUrl": v['videoUrl']}
        
        current_data = []
        if os.path.exists(JSON_OUTPUT_PATH):
            try:
                with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f: current_data = json.load(f)
            except: pass
            
        all_data = [new_item] + current_data
        unique_data = {item['id']: item for item in all_data}.values()
        sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
        with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
            
        print(f"      Successfully saved and updated JSON for {v['id']}")
        time.sleep(5)
    conn.close()
    
    # 잔여 임시 파일 정리 (.part 파일 등)
    for f in glob.glob("temp_audio_*"):
        try: os.remove(f)
        except: pass
        
    print("Done!")

if __name__ == "__main__":
    main()
