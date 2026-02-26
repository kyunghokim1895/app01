import json
import os

files = [
    "/Users/kimkyungho/Developer/app01/HKKoreaApp/src/services/data.json",
    "/Users/kimkyungho/Developer/app01/HKGlobalApp/src/services/data.json",
    "/Users/kimkyungho/Developer/app01/JipconomyApp/src/services/data.json",
    "/Users/kimkyungho/Developer/app01/MKSummaryApp/src/services/data.json"
]

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 요약이 비어있는 항목 제거
        cleaned_data = [item for item in data if item.get('summary') and item.get('summary').strip()]
        
        # 날짜 내림차순 정렬 (최신순)
        # publishedAt이 없는 경우 빈 문자열로 처리하여 가장 뒤로 보냄
        sorted_data = sorted(cleaned_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        print(f"Cleaned and sorted {file_path} (Removed {len(data) - len(cleaned_data)} empty entries)")
