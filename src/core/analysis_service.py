import os
import json
import re
import google.generativeai as genai

class AnalysisService:
    def __init__(self, gemini_api_key):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for AnalysisService")
        self.gemini_api_key = gemini_api_key
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        genai.configure(api_key=gemini_api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')

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

    def summarize_from_metadata(self, title, description, channel_name=""):
        """영상의 제목과 설명을 기반으로 Gemini를 사용하여 분석합니다."""
        source = channel_name or "경제/투자 관련 유튜브 채널"

        # description이 비어있거나 너무 짧은 경우 제목만으로 분석
        has_description = description and len(description.strip()) > 20

        if has_description:
            prompt = f"""아래는 '{source}' 채널의 유튜브 영상 제목과 설명이야.
이 정보를 바탕으로 영상이 다루는 내용을 추론하여 한국어로 정리해줘.

제목: {title}
설명: {description}

다음 형식을 지켜줘:
1. 영상이 다루는 내용을 1~2문장으로 서술형 요약 (summary 필드)
2. 영상에서 다룰 것으로 예상되는 핵심 주제 5개를 문장으로 작성 (summaryList 필드)
3. 관련 핵심 키워드를 #으로 시작하는 태그 4개 (keywords 필드)

응답은 반드시 순수 JSON 형식으로만 해줘:
{{
    "summary": "서술형 요약",
    "summaryList": ["1. 문장", "2. 문장", "3. 문장", "4. 문장", "5. 문장"],
    "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
}}"""
        else:
            prompt = f"""아래는 '{source}' 채널의 유튜브 영상 제목이야.
이 제목을 바탕으로 영상이 다루는 내용을 추론하여 한국어로 정리해줘.

제목: {title}

다음 형식을 지켜줘:
1. 영상이 다루는 내용을 1~2문장으로 서술형 요약 (summary 필드)
2. 영상에서 다룰 것으로 예상되는 핵심 주제 5개를 문장으로 작성 (summaryList 필드)
3. 관련 핵심 키워드를 #으로 시작하는 태그 4개 (keywords 필드)

응답은 반드시 순수 JSON 형식으로만 해줘:
{{
    "summary": "서술형 요약",
    "summaryList": ["1. 문장", "2. 문장", "3. 문장", "4. 문장", "5. 문장"],
    "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"]
}}"""

        try:
            response = self.model.generate_content(prompt)
            return self.parse_json_from_gemini(response.text)
        except Exception as e:
            print(f"  > Gemini Error: {e}")
            return None
