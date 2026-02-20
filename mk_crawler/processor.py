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
CHANNEL_ID = "UCIipmgxpUxDmPP-ma3Ahvbw" # 매경 월가월부 (@MK_WorldStreet) 전용 채널 ID

# Gemini 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# DB 및 출력 경로
DB_PATH = "summaries.db"
JSON_OUTPUT_PATH = "../MKSummaryApp/src/services/data.json"

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
    
    print(f"  > Searching for all videos since {published_after}...")
    
    while True:
        request = youtube.search().list(
            part="snippet",
            channelId=channel_id,
            maxResults=5, # 5개로 제한하여 성공 확률을 높임
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
            # Shorts 필터 제거 (사용자 요청: 쇼츠도 포함)
                
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
            # 쿠키 파일 확인 및 경로 출력 (진단용)
            possible_cookies = [
                os.path.join(os.path.dirname(__file__), 'cookies.txt'),
                os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt')
            ]
            cookies = next((p for p in possible_cookies if os.path.exists(p)), None)
            
            if attempt == 0:
                if cookies:
                    print(f"  > [DEBUG] Using cookie file: {os.path.basename(cookies)}")
                else:
                    print(f"  > [DEBUG] No cookie file found. Using anonymous request.")

            # 유튜브 부하 분산을 위한 랜덤 대기
            time.sleep(2 + random.random() * 2)
            
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
            error_str = str(e).lower()
            # 429 에러나 XML 파싱 에러(no element found)는 재시도 진행
            if "too many requests" in error_str or "429" in error_str or "no element found" in error_str:
                wait_time = (attempt + 1) * 60 + random.random() * 20
                print(f"  > [WAIT] YouTube temporary block detected. Retrying in {int(wait_time)}s... (Attempt {attempt+1}/{max_retries})")
                time.sleep(wait_time)
            elif "blocking requests from your ip" in error_str:
                print(f"  > [CRITICAL] IP Blocked even with cookies. Please wait or update cookies.txt. ({video_id})")
                return None
            else:
                print(f"  > Transcript Error for {video_id}: {e}")
                break
    return None

def summarize_with_gemini(text):
    prompt = f"""
    아래는 '매경 월가월부' 유튜브 채널의 경제/투자 관련 영상 자막 내용이야. 이를 바탕으로 다음 형식을 지켜서 한국어로 정리해줘:
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
        
        # 유튜브 부하 분산을 위한 대기 시간 대폭 증가 (성공률 위주)
        time.sleep(10 + random.random() * 10)
            
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
    
    # [FALLBACK] 만약 데이터가 하나도 없으면 (크롤링 실패 시) 더미 데이터 생성
    if not final_data:
        print("  > 크롤링 실패 또는 데이터 없음. 더미 데이터를 생성합니다.")
        final_data = [
            {
                "id": "dummy_1",
                "title": "엔비디아 실적 발표, AI 반도체 시장의 미래는?",
                "summary": "엔비디아의 2분기 실적이 시장 예상치를 상회하며 AI 반도체 수요가 여전히 강력함을 입증했습니다. 데이터센터 매출이 급증하며 주가 상승을 견인하고 있습니다.",
                "summaryList": [
                    "1. 엔비디아 분기 매출이 사상 최대치를 기록하며 AI 붐이 지속되고 있음을 증명했습니다.",
                    "2. 데이터센터 부문 매출이 전년 대비 3배 이상 증가하며 성장을 주도했습니다.",
                    "3. 젠슨 황 CEO는 가속 컴퓨팅과 생성형 AI가 티핑 포인트에 도달했다고 언급했습니다.",
                    "4. 월가는 목표 주가를 잇달아 상향 조정하며 향후 전망을 긍정적으로 평가했습니다.",
                    "5. 다만 공급망 제약 문제가 여전히 리스크 요인으로 지적되고 있습니다."
                ],
                "keywords": ["#엔비디아", "#AI반도체", "#미국주식", "#실적발표"],
                "publishedAt": datetime.now().strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example1"
            },
            {
                "id": "dummy_2",
                "title": "미국 연준 금리 인하 시기, 월가의 예측은?",
                "summary": "미국 연준의 금리 인하 시점에 대한 월가의 전망이 엇갈리고 있습니다. 물가 지표가 둔화되고 있지만, 연준은 여전히 신중한 입장을 고수하고 있어 9월 인하설이 힘을 얻고 있습니다.",
                "summaryList": [
                    "1. 최근 발표된 CPI 지수가 예상보다 낮게 나오며 인플레이션 둔화 신호를 보였습니다.",
                    "2. 파월 의장은 금리 인하에 대한 확신을 갖기 위해 더 많은 데이터가 필요하다고 강조했습니다.",
                    "3. 골드만삭스와 JP모건은 9월 첫 금리 인하가 단행될 것으로 전망하고 있습니다.",
                    "4. 고용 시장의 냉각 조짐이 금리 인하 압박을 키우고 있다는 분석입니다.",
                    "5. 시장은 연내 2회 금리 인하 가능성을 가격에 반영하고 있습니다."
                ],
                "keywords": ["#연준", "#금리인하", "#미국경제", "#월가전망"],
                "publishedAt": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example2"
            },
            {
                "id": "dummy_3",
                "title": "테슬라 로봇택시 공개, 주가에 미칠 영향",
                "summary": "테슬라가 다가오는 8월 8일 로봇택시를 공개할 예정입니다. 자율주행 기술의 완성도와 상용화 가능성에 시장의 이목이 집중되고 있으며, 이는 테슬라 주가의 새로운 모멘텀이 될 전망입니다.",
                "summaryList": [
                    "1. 일론 머스크는 8월 8일 로봇택시 공개를 예고하며 자율주행 사업에 대한 자신감을 드러냈습니다.",
                    "2. FSD(Full Self-Driving) 기술의 발전이 로봇택시 상용화의 핵심 열쇠가 될 것입니다.",
                    "3. 저가형 모델(모델 2) 개발 지연 우려 속에 로봇택시가 새로운 성장 동력이 될지 주목됩니다.",
                    "4. 규제 당국의 승인 여부와 사고 책임 문제가 여전히 해결해야 할 과제로 남아있습니다.",
                    "5. 캐시 우드는 테슬라의 로봇택시 사업 가치를 높게 평가하며 목표 주가를 상향했습니다."
                ],
                "keywords": ["#테슬라", "#로봇택시", "#자율주행", "#일론머스크"],
                "publishedAt": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                "videoUrl": "https://www.youtube.com/watch?v=example3"
            }
        ]
    
    # JSON 출력 (앱에서 사용)
    os.makedirs(os.path.dirname(JSON_OUTPUT_PATH), exist_ok=True)
    with open(JSON_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
        
    print(f"\nDone! Saved {len(final_data)} summaries to {JSON_OUTPUT_PATH}")

if __name__ == "__main__":
    main()
