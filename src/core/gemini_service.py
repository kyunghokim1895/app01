import os
import sys
import time
import json
import re
import subprocess
import google.generativeai as genai

def init_gemini(api_key):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel('gemini-2.0-flash')

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
    except Exception:
        return None

def summarize_with_gemini(model, text):
    if not text: return None
    prompt = f"다음 영상을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) JSON으로 작성해줘: {text}"
    try:
        response = model.generate_content(prompt)
        return parse_json_from_gemini(response.text)
    except Exception:
        return None

def summarize_from_video(model, video_id):
    """
    영상을 다운로드(최저화질)하여 Gemini의 멀티모달 기능을 통해 
    시각 정보(자막, 도표)와 오디오를 함께 분석합니다.
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    video_path = f"temp_video_{video_id}.mp4"
    
    # Cookie Handling
    env_cookies = os.getenv("YOUTUBE_COOKIES")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(os.path.dirname(current_dir))
    temp_cookie_path = os.path.join(root_dir, f"temp_cookies_v_{video_id}.txt")
    
    cookies = None
    if env_cookies:
        try:
            with open(temp_cookie_path, "w") as f: f.write(env_cookies)
            cookies = temp_cookie_path
        except Exception: pass
    else:
        possible_cookies = [
            os.path.join(root_dir, 'cookies.txt'),
            os.path.join(root_dir, 'www.youtube.com_cookies.txt')
        ]
        cookies = next((p for p in possible_cookies if os.path.exists(p)), None)

    # Bypassing strategies: Use 'tv' and 'web_embedded' clients as they often bypass datacenter IP blocks
    cmd = [
        sys.executable, "-m", "yt_dlp", 
        "-f", "worst", 
        "-o", video_path, 
        "--max-filesize", "50M", 
        "--js-runtimes", "node",
        "--user-agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "--extractor-args", "youtube:player-client=tv,web_embedded",
        "--no-check-certificates"
    ]
    if cookies:
        cmd.extend(["--cookies", cookies])
    cmd.append(url)
    
    try:
        print(f"      Downloading low-res video for {video_id}...")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"      yt-dlp error output: {result.stderr}")
            if "Sign in to confirm you" in result.stderr:
                print("      [CRITICAL] YouTube blocked this IP or cookie is invalid. Manual cookie refresh is likely needed.")
            if os.path.exists(temp_cookie_path): os.remove(temp_cookie_path)
            return None
        
        if not os.path.exists(video_path):
            print(f"      Video file not found after download: {video_path}")
            return None
            
        print(f"      Uploading video to Gemini (Multimodal)...")
        sample_file = genai.upload_file(path=video_path, display_name=f"Video_{video_id}")
        
        # Wait for file to be ready
        while sample_file.state.name == "PROCESSING":
            time.sleep(2)
            sample_file = genai.get_file(sample_file.name)
            
        print(f"      Generating multimodal summary (Visual+Audio)...")
        prompt = """영상의 화면(자막, 도표, 자료화면)과 오디오 내용을 모두 참고해서 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) 포맷으로 분석해줘.
반드시 아래와 같은 형태의 순수 JSON 객체로만 응답하고, 마크다운(```json 등)이나 다른 설명은 절대 추가하지 마:
{
  "summary": "화면 정보와 말을 종합한 한글 요약",
  "summaryList": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3", "핵심 포인트 4", "핵심 포인트 5"],
  "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
}"""
        response = model.generate_content(
            [sample_file, prompt],
            generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
        )
        
        genai.delete_file(sample_file.name)
        os.remove(video_path)
        if os.path.exists(temp_cookie_path): os.remove(temp_cookie_path)
        return parse_json_from_gemini(response.text)
    except Exception as e:
        print(f"      Error in summarize_from_video: {str(e)}")
        if os.path.exists(video_path): os.remove(video_path)
        if os.path.exists(temp_cookie_path): os.remove(temp_cookie_path)
    return None

# For backward compatibility if needed by other files
summarize_from_audio = summarize_from_video
