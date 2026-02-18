import os
import sqlite3
import json
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

def get_video_list(api_key, channel_id, months=6):
    youtube = googleapiclient.discovery.build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.utcnow() - timedelta(days=months*30)).isoformat() + "Z"
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
        
        for item in response.get("items", []):
            title = html.unescape(item["snippet"]["title"])
            # 더 포괄적인 필터
            if any(x in title for x in ["#1분뉴스", "#1분 뉴스", "#쇼츠", "Shorts", "#숏폼"]):
                continue
                
            videos.append({
                "id": item["id"]["videoId"],
                "title": title,
                "publishedAt": item["snippet"]["publishedAt"][:10],
                "videoUrl": f"https://www.youtube.com/watch?v={item['id']['videoId']}"
            })
            
        if len(videos) >= 50:
            break
        next_page_token = response.get("nextPageToken")
        if not next_page_token: break
    return videos

def get_transcript(video_id):
    try:
        api = YouTubeTranscriptApi()
        transcript_list = api.list(video_id)
        try:
            transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
        except:
            transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
            
        data = transcript.fetch()
        # 이 버전에서는 객체이므로 .text로 접근해야 할 수도 있습니다.
        try:
            return " ".join([i.text for i in data])
        except:
            return " ".join([i['text'] for i in data])
    except Exception as e:
        print(f"  > Transcript Error for {video_id}: {e}")
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
    
    # 1. 영상 목록 가져오기 (3개월치)
    videos = get_video_list(YOUTUBE_API_KEY, CHANNEL_ID, months=3)
    print(f"Found {len(videos)} videos.")
    
    final_data = []
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    for i, v in enumerate(videos):
        print(f"[{i+1}/{len(videos)}] Processing: {v['title']}")
        
        # 기 저장 확인
        cursor.execute("SELECT * FROM videos WHERE id=?", (v['id'],))
        row = cursor.fetchone()
        
        if row:
            print("  > Already exists in DB.")
            final_data.append({
                "id": row[0],
                "title": row[1],
                "summary": row[2],
                "summaryList": json.loads(row[3]),
                "keywords": json.loads(row[4]),
                "publishedAt": row[5],
                "videoUrl": row[6]
            })
            continue
            
        # 자막 추출
        transcript = get_transcript(v['id'])
        if not transcript:
            continue
            
        # 요약
        analysis = summarize_with_gemini(transcript)
        if not analysis:
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
        
        # DB 저장
        cursor.execute(
            "INSERT INTO videos VALUES (?,?,?,?,?,?,?)",
            (entry['id'], entry['title'], entry['summary'], json.dumps(entry['summaryList']), json.dumps(entry['keywords']), entry['publishedAt'], entry['videoUrl'])
        )
        conn.commit()
        
        final_data.append(entry)
        time.sleep(1) # API 레이트 리밋 방지
        
    conn.close()
    
    # JSON 출력 (앱에서 사용)
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone! Saved {len(final_data)} summaries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
