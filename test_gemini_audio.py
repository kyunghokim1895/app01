import os
import google.generativeai as genai
from dotenv import load_dotenv
import time

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash-lite')

audio_path = "temp_audio_rF-dBu2eMw4.m4a"
print("Uploading...")
sample_file = genai.upload_file(path=audio_path)

while sample_file.state.name == "PROCESSING":
    print("Processing...")
    time.sleep(2)
    sample_file = genai.get_file(sample_file.name)

print(f"File state: {sample_file.state.name}")

if sample_file.state.name == "ACTIVE":
    print("Generating...")
    prompt = "오디오 내용을 1.한글요약(summary), 2.5문장리스트(summaryList), 3.#키워드4개(keywords) JSON으로 작성해줘."
    try:
        response = model.generate_content([sample_file, prompt])
        print("Response text:")
        print(response.text)
    except Exception as e:
        print(f"Generation error: {e}")
        try:
            print(response.prompt_feedback)
        except: pass

genai.delete_file(sample_file.name)
