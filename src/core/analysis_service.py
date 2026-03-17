import os
import sys
import json
import random
import time
import subprocess
import re
import glob
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai

class AnalysisService:
    def __init__(self, gemini_api_key):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for AnalysisService")
        self.gemini_api_key = gemini_api_key
        # 라이브러리 설정 및 환경변수 백업 (일부 버전 대응)
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

    def clean_vtt(self, vtt_text):
        """VTT 자막 파일에서 태그와 타임스탬프를 제거하고 순수 텍스트만 추출합니다."""
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

    def get_transcript_via_ytdlp(self, video_id):
        """yt-dlp를 사용하여 차단을 우회하고 자막을 가져옵니다."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        temp_prefix = f"temp_sub_{video_id}"
        
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-lang", "ko",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            "-o", temp_prefix,
        ]
        
        # 쿠키 파일 확인
        possible_cookies = [
            os.path.join(os.getcwd(), 'cookies.txt'),
            os.path.join(os.getcwd(), 'www.youtube.com_cookies.txt'),
            os.path.join(os.path.dirname(os.getcwd()), 'cookies.txt') # 상위 폴더도 확인
        ]
        cookie_file = next((p for p in possible_cookies if os.path.exists(p)), None)
        if cookie_file:
            cmd.extend(["--cookies", cookie_file])
        
        cmd.append(url)
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=60)
            files = glob.glob(f"{temp_prefix}*")
            sub_file = next((f for f in files if f.endswith(('.vtt', '.srt'))), None)
            
            if sub_file:
                with open(sub_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                for f in files: os.remove(f)
                return self.clean_vtt(content) if sub_file.endswith('.vtt') else content
            else:
                print(f"  > [FALLBACK INFO] No subtitle files found by yt-dlp.")
        except Exception as e:
            print(f"  > [FALLBACK ERROR] yt-dlp fetch failed: {str(e)[:200]}")
            for f in glob.glob(f"{temp_prefix}*"): os.remove(f)
        return None

    def get_transcript(self, video_id, cookies_path=None):
        """YouTubeTranscriptApi를 사용하여 자막을 가져옵니다. 실패 시 yt-dlp로 우회합니다."""
        max_retries = 2
        for attempt in range(max_retries):
            try:
                time.sleep(2 + random.random() * 2)
                
                # 전역 환경변수 쿠키 처리 (GHA용)
                env_cookies = os.getenv("YOUTUBE_COOKIES")
                current_cookies = cookies_path
                
                if env_cookies and not current_cookies:
                    temp_cookie_path = "temp_cookies_shared.txt"
                    with open(temp_cookie_path, "w") as f:
                        f.write(env_cookies)
                    current_cookies = temp_cookie_path

                if current_cookies:
                    transcript_list = YouTubeTranscriptApi().list(video_id, cookies=current_cookies)
                else:
                    transcript_list = YouTubeTranscriptApi().list(video_id)
                    
                try:
                    transcript = transcript_list.find_transcript(['ko', 'ko-KR'])
                except:
                    transcript = transcript_list.find_generated_transcript(['ko', 'ko-KR'])
                    
                data = transcript.fetch()
                # 텍스트 추출 (딕셔너리 또는 객체 형태 모두 대응)
                texts = []
                for i in data:
                    if isinstance(i, dict):
                        texts.append(i.get('text', ''))
                    else:
                        texts.append(getattr(i, 'text', ''))
                return " ".join(texts)

            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["too many requests", "429", "no element found"]):
                    print(f"  > [API BLOCKED] YouTube API blocked. Attempting yt-dlp fallback...")
                    fallback_text = self.get_transcript_via_ytdlp(video_id)
                    if fallback_text: return fallback_text
                    
                    wait_time = (attempt + 1) * 30 + random.random() * 10
                    print(f"  > [WAIT] Retrying in {int(wait_time)}s...")
                    time.sleep(wait_time)
                else:
                    print(f"  > Transcript Error for {video_id}: {e}")
                    break
        return None

    def parse_json_from_gemini(self, text_resp):
        """Gemini 응답에서 JSON 부분을 추출하여 파싱합니다."""
        try:
            if "```" in text_resp:
                json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_resp, re.DOTALL)
                if json_match:
                    text_resp = json_match.group(1)
                else:
                    text_resp = re.sub(r"```(json)?", "", text_resp).strip()
            result = json.loads(text_resp)
            return {
                "summary": result.get("summary", result.get("요약", "")),
                "summaryList": result.get("summaryList", result.get("요점", result.get("핵심내용", []))),
                "keywords": result.get("keywords", result.get("키워드", []))
            }
        except Exception as e:
            print(f"  > Gemini/JSON Error: {e}")
            return None

    def summarize_with_gemini(self, text, custom_prompt_header=""):
        """자막 텍스트를 Gemini를 사용하여 요약합니다."""
        header = custom_prompt_header or "경제/투자 관련 영상 자막 내용"
        prompt = f"""
        아래는 '{header}'이야. 이를 바탕으로 다음 형식을 지켜서 한국어로 정리해줘:
        1. 전체 내용을 아우르는 1~2문장의 짧은 서술형 요약을 작성할 것. (summary 필드)
        2. 핵심 내용을 5개 문장의 번호 리스트로 작성할 것 (1., 2., 3., 4., 5.) (summaryList 필드)
        3. 영상과 관련된 핵심 키워드를 #으로 시작하는 태그 4개 정도 뽑아줄 것. (keywords 필드)
        
        응답은 반드시 순수 JSON 형식으로만 해줘:
        {{
            "summary": "서술형 요약",
            "summaryList": ["1. 문장", "2. 문장", "3. 문장", "4. 문장", "5. 문장"],
            "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
        }}
        
        내용:
        {text}
        """
        try:
            response = self.model.generate_content(prompt)
            return self.parse_json_from_gemini(response.text)
        except Exception as e:
            print(f"  > Gemini Error: {e}")
            return None

    def summarize_from_audio(self, video_id):
        """자막이 없을 때 영상을 직접 '듣고' 요약합니다."""
        url = f"https://www.youtube.com/watch?v={video_id}"
        audio_path = f"temp_audio_{video_id}.m4a"
        print(f"  > [ULTIMATE FALLBACK] Downloading audio for direct listening analysis...")
        
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", "ba[ext=m4a]",
            "-o", audio_path,
            "--max-filesize", "20M",
            "--js-runtimes", "node",
            "--remote-components", "ejs:github",
            url
        ]
        
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=180)
            if not os.path.exists(audio_path): return None
            
            print(f"  > [OK] Audio downloaded. Uploading to Gemini...")
            sample_file = genai.upload_file(path=audio_path, display_name=f"Audio_{video_id}")
            
            prompt = """오디오 내용을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) 포맷으로 분석해줘.
            반드시 아래와 같은 형태의 순수 JSON 객체로만 응답해:
            {
              "summary": "요약",
              "summaryList": ["1", "2", "3", "4", "5"],
              "keywords": ["#1", "#2", "#3", "#4"]
            }"""
            
            response = self.model.generate_content(
                [sample_file, prompt],
                generation_config=genai.types.GenerationConfig(response_mime_type="application/json")
            )
            
            genai.delete_file(sample_file.name)
            os.remove(audio_path)
            return self.parse_json_from_gemini(response.text)
        except Exception as e:
            print(f"  > [ULTIMATE ERROR] Audio analysis failed: {e}")
            if os.path.exists(audio_path): os.remove(audio_path)
        return None
