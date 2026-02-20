import os
import random
import time
from youtube_transcript_api import YouTubeTranscriptApi

def check_youtube_status():
    # 테스트용 비디오 ID (최근 인기 영상 중 하나)
    test_video_id = "6SRmFEaHRu8" # 최근 월가월부 라이브 영상
    
    print(f"--- YouTube Connection Diagnostics ---")
    
    # 쿠키 확인
    possible_cookies = [
        os.path.join(os.path.dirname(__file__), 'cookies.txt'),
        os.path.join(os.path.dirname(__file__), 'www.youtube.com_cookies.txt'),
        os.path.join(os.path.dirname(__file__), '../mk_crawler/cookies.txt'),
        os.path.join(os.path.dirname(__file__), '../mk_crawler/www.youtube.com_cookies.txt')
    ]
    cookies = next((p for p in possible_cookies if os.path.exists(p)), None)
    
    if cookies:
        print(f"[INFO] Using cookie file: {os.path.basename(cookies)}")
    else:
        print("[WARNING] No cookie file found. Testing anonymously.")

    try:
        print(f"[STEP] Attempting to fetch transcript for video: {test_video_id}")
        if cookies:
            transcript_list = YouTubeTranscriptApi.list_transcripts(test_video_id, cookies=cookies)
        else:
            transcript_list = YouTubeTranscriptApi.list_transcripts(test_video_id)
            
        # 자막 리스트 가져오기 성공 여부 확인
        print("[SUCCESS] Successfully reached YouTube API!")
        print("[SUCCESS] Your IP is NOT blocked for metadata requests.")
        
        # 실제 데이터 페치 시도
        transcript = transcript_list.find_transcript(['ko', 'en'])
        transcript.fetch()
        print("[SUCCESS] Full transcript fetch successful! You are completely clear.")
        
    except Exception as e:
        error_str = str(e).lower()
        if "too many requests" in error_str or "429" in error_str:
            print("[STATUS] BLOCKED: Still under 'Too Many Requests' (429) rate limit.")
            print("        Please wait 1-2 hours or use a mobile hotspot.")
        elif "blocking requests from your ip" in error_str:
            print("[STATUS] CRITICAL BLOCK: YouTube is explicitly blocking your IP.")
            print("        Cookies might be expired, or the block is severe. Use a mobile hotspot.")
        else:
            print(f"[STATUS] ERROR: {e}")
            print("        Note: If it says 'Subtitles are disabled', the connection worked but this specific video has no CC.")

if __name__ == "__main__":
    check_youtube_status()
