import os
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

def summarize_from_audio(model, video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    audio_path = f"temp_audio_{video_id}.m4a"
    # Increased to 100M for long videos
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
        prompt = "오디오 내용을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) JSON으로 작성해줘."
        response = model.generate_content([sample_file, prompt])
        
        genai.delete_file(sample_file.name)
        os.remove(audio_path)
        return parse_json_from_gemini(response.text)
    except Exception as e:
        print(f"      Error in summarize_from_audio: {str(e)}")
        if os.path.exists(audio_path): os.remove(audio_path)
    return None
