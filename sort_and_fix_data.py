import json
import os

files = [
    "/Users/kimkyungho/app01/HKKoreaApp/src/services/data.json",
    "/Users/kimkyungho/app01/HKGlobalApp/src/services/data.json",
    "/Users/kimkyungho/app01/JipconomyApp/src/services/data.json",
    "/Users/kimkyungho/app01/MKSummaryApp/src/services/data.json"
]

for file_path in files:
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 날짜 내림차순 정렬 (최신순)
        sorted_data = sorted(data, key=lambda x: x.get('publishedAt', ''), reverse=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(sorted_data, f, ensure_ascii=False, indent=2)
        print(f"Sorted {file_path}")
