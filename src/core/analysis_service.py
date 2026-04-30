import os
import json
import re
import time
from google import genai

# 카테고리 목록 (프론트엔드와 동기화)
CATEGORIES = ["국내증시", "해외증시", "부동산", "가상자산", "경제정책", "산업/기업", "채권/환율", "재테크"]

_TRANSIENT_TOKENS = (
    "429", "500", "502", "503", "504",
    "resource_exhausted", "resource exhausted",
    "internal", "bad gateway", "unavailable",
    "deadline", "overloaded", "high demand",
)


def _is_transient_error(err: Exception) -> bool:
    msg = str(err).lower()
    return any(tok in msg for tok in _TRANSIENT_TOKENS)


def _call_with_retry(fn, *, max_retries=3, base_delay=5.0):
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as e:
            if attempt < max_retries and _is_transient_error(e):
                delay = base_delay * (attempt + 1)
                print(f"  > Gemini transient error (attempt {attempt + 1}/{max_retries + 1}): {e}")
                print(f"  > Retrying in {delay:.0f}s...")
                time.sleep(delay)
                continue
            raise


class AnalysisService:
    def __init__(self, gemini_api_key):
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY is required for AnalysisService")
        self.gemini_api_key = gemini_api_key
        os.environ["GOOGLE_API_KEY"] = gemini_api_key
        self.model_name = 'gemini-2.5-flash-lite'
        self.client = genai.Client(api_key=gemini_api_key)

    def parse_json_from_gemini(self, text_resp, categories=None):
        """Gemini 응답에서 JSON 부분을 추출하여 파싱합니다."""
        valid_categories = categories or CATEGORIES
        default_category = valid_categories[-1]  # 마지막 카테고리를 기본값으로 사용
        try:
            if "```" in text_resp:
                json_match = re.search(r"```(?:json)?\s*(.*?)\s*```", text_resp, re.DOTALL)
                if json_match:
                    text_resp = json_match.group(1)
                else:
                    text_resp = re.sub(r"```(json)?", "", text_resp).strip()
            result = json.loads(text_resp)

            # category 유효성 검증
            category = result.get("category", "")
            if category not in valid_categories:
                category = default_category

            return {
                "summary": result.get("summary", result.get("요약", "")),
                "summaryList": result.get("summaryList", result.get("요점", result.get("핵심내용", []))),
                "keywords": result.get("keywords", result.get("키워드", [])),
                "category": category
            }
        except Exception as e:
            print(f"  > Gemini/JSON Error: {e}")
            return None

    def summarize_from_metadata(self, title, description, channel_name="", categories=None):
        """영상의 제목과 설명을 기반으로 Gemini를 사용하여 분석합니다."""
        source = channel_name or "경제/투자 관련 유튜브 채널"
        use_categories = categories or CATEGORIES
        categories_str = ", ".join(use_categories)

        # description이 비어있거나 너무 짧은 경우 제목만으로 분석
        has_description = description and len(description.strip()) > 20

        content_section = f"제목: {title}\n설명: {description}" if has_description else f"제목: {title}"
        content_label = "제목과 설명" if has_description else "제목"

        prompt = f"""아래는 '{source}' 채널의 유튜브 영상 {content_label}이야.
이 정보를 바탕으로 영상이 다루는 내용을 추론하여 한국어로 정리해줘.

{content_section}

다음 형식을 지켜줘:
1. 영상이 다루는 내용을 1~2문장으로 서술형 요약 (summary 필드)
2. 영상에서 다룰 것으로 예상되는 핵심 주제 5개를 문장으로 작성 (summaryList 필드)
3. 관련 핵심 키워드를 #으로 시작하는 태그 4개 (keywords 필드)
4. 다음 카테고리 중 가장 적합한 것 1개를 선택 (category 필드): {categories_str}

응답은 반드시 순수 JSON 형식으로만 해줘:
{{
    "summary": "서술형 요약",
    "summaryList": ["1. 문장", "2. 문장", "3. 문장", "4. 문장", "5. 문장"],
    "keywords": ["#키워드1", "#키워드2", "#키워드3", "#키워드4"],
    "category": "카테고리"
}}"""

        try:
            response = _call_with_retry(
                lambda: self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                )
            )
            return self.parse_json_from_gemini(response.text, categories=use_categories)
        except Exception as e:
            print(f"  > Gemini Error: {e}")
            return None
