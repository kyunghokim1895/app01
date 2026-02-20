import os
import sqlite3
import json
import random
from datetime import datetime, timedelta
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import googleapiclient.discovery
import time
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# === 설정 ===
# .env 파일에 저장된 키를 가져옵니다.
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CHANNEL_ID = "UC3p-0EWA8OXko2EUDUXAy5w" # 서울경제TV 공식 채널 ID

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../SentvSummaryApp/src/services/data.json"

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

def get_video_list(api_key, channel_id):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    # 사용자 요청: 정확히 오늘 데이터부터 시작 (과도한 요청 방지)
    published_after = "2026-02-20T00:00:00Z"
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
        print(f"  > API returned {len(items)} items in this batch. (Total so far: {len(videos) + len(items)})")
        
        for item in items:
            title = html.unescape(item["snippet"]["title"])
            # 사용자 요청: 쇼츠(#Shorts) 포함 (필터 제거)
                
            videos.append({
                "id": item["id"]["videoId"],
                "title": title,
                "publishedAt": item["snippet"]["publishedAt"][:10],
                "videoUrl": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
            
        next_page_token = response.get("nextPageToken")
        if not next_page_token or len(videos) >= 5: break
    return videos

def get_transcript(video_id):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # 유튜브 부하 분산을 위한 랜덤 대기 (인간처럼 보이게 함)
            time.sleep(2 + random.random() * 2)
            
            # 쿠키 파일이 있으면 사용 (IP 차단 우회용)
            possible_cookies = [
                os.path.join(os.path.dirname(__file__), 'cookies.txt'),
                os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')
            ]
            cookies = next((p for p in possible_cookies if os.path.exists(p)), None)
            
            # 0.6.2 버전부터는 list_transcripts 정적 메서드 사용 권장
            if cookies:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id, cookies=cookies)
            else:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                
            try:
                transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
            except:
                transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
                
            data = transcript.fetch()
            result = []
            for i in data:
                if isinstance(i, dict):
                    result.append(i.get('text', ''))
                else:
                    try:
                        result.append(getattr(i, 'text', ''))
                    except:
                        result.append(str(i))
            return " ".join(result)

        except Exception as e:
            error_str = str(e)
            if "Too Many Requests" in error_str or "429" in error_str:
                wait_time = (attempt + 1) * 60 + random.random() * 15 # 차단 시 더 넉넉히 대기
                print(f"  > [WAIT] Too Many Requests. Retrying in {int(wait_time)}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif "YouTube is blocking requests from your IP" in error_str:
                print(f"  > [CRITICAL] IP Blocked even with cookies. Check cookies.txt or wait. ({video_id})")
                return None
            else:
                print(f"  > Transcript Error for {video_id}: {e}")
                break
    return None

def summarize_with_gemini(text):
    prompt = f"""
    아래는 경제 뉴스 영상의 자막 내용이야. 이를 바탕으로 다음 형식을 지켜서 한국어로 정리해줘:
    1. 전체 내용을 아우르는 1~2문장의 짧은 서술형 요약을 작성할 것. (summary 필드)
    2. 핵심 내용을 5개 문장의 번호 리스트로 작성할 것 (1., 2., 3., 4., 5.) (summaryList 필드)
    3. 영상과 관련된 핵심 키워드를 #으로 시작하는 태그 4개 정도 뽑아줄 것. (keywords 필드)
    
    응답은 반드시 순수 JSON 형식으로만 해줘:
    {{
        "summary": "서술형 요약",
        "summaryList": ["1. 문장", "2. 문장", "3. 문장", "4. 문장", "5. 문장"],
        "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
    }}
    
    자막 내용:
    {text}
    """
    try:
        response = model.generate_content(prompt)
        text_resp = response.text.strip()
        
        # ```json 마크다운 제거
        if "```" in text_resp:
            import re
            json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_resp, re.DOTALL)
            if json_match:
                text_resp = json_match.group(1)
            else:
                text_resp = re.sub(r"```(json)?", "", text_resp).strip()
                
        result = json.loads(text_resp)
        return result
    except Exception as e:
        print(f"  > Gemini/JSON Error: {e}")
        return None

def main():
    init_db()
    
    # 1. 기존 JSON 데이터 로드 (메모리 역할)
    # GitHub Action 환경은 DB파일이 초기화되므로 JSON을 기본 저장소로 활용합니다.
    existing_data = []
    if os.path.exists(JSON_OUTPUT_PATH):
        try:
            with open(JSON_OUTPUT_PATH, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            print(f"  > 로컬 JSON에서 {len(existing_data)}개의 기존 데이터를 불러왔습니다.")
        except Exception as e:
            print(f"  > JSON 로드 중 오류: {e}")
            
    existing_ids = {item['id'] for item in existing_data}

    # 2. 영상 목록 가져오기 (2026년 이후 전수 조사)
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID)
    print(f"  > [DEBUG] YouTube API returned total {len(videos)} videos.")
    
    if not videos:
        print("  > [WARNING] No videos found. Check Channel ID or API Key.")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    new_entries = []
    
    for i, v in enumerate(videos):
        # 3. DB 또는 기존 JSON에 있는지 확인
        cursor.execute("SELECT id FROM videos WHERE id=?", (v['id'],))
        if cursor.fetchone() or v['id'] in existing_ids:
            continue
            
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']} ({v['id']})")
        
        # 유튜브 부하 분산을 위한 랜덤 대기 (인간처럼 보이게 함)
        time.sleep(3 + random.random() * 3)
            
        # 자막 추출
        transcript = get_transcript(v['id'])
        if not transcript:
            print(f"  > [SKIP] No transcript found for {v['id']}")
            continue
            
        print(f"  > [OK] Transcript found. Length: {len(transcript)}")
        # 요약
        analysis = summarize_with_gemini(transcript)
        if not analysis:
            print(f"  > [ERROR] Gemini summarization failed for {v['id']}")
            continue
            
        # 결과 결합
        entry = {
            "id": v['id'],
            "title": v['title'],
            "summary": analysis.get("summary", ""),
            "summaryList": analysis.get("summaryList", []),
            "keywords": analysis.get("keywords", []),
            "publishedAt": v['publishedAt'],
            "videoUrl": v['videoUrl']
        }
        
        new_entries.append(entry)
        time.sleep(5) # Gemini Free Tier RPM(15) 준수를 위해 넉넉히 대기
        
    conn.close()
    
    # 4. 결과 병합 (새로운 것 + 기존 것)
    # get_video_list가 최신순으로 가져오므로 new_entries를 앞에 둠
    final_data = new_entries + existing_data
    
    # JSON 출력 (앱에서 사용)
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone! Saved {len(final_data)} summaries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
