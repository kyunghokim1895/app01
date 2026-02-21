import json
import os
import sqlite3

projects = [
    {"name": "HKKorea", "json": "HKKoreaApp/src/services/data.json", "db": "hk_korea_crawler/summaries.db"},
    {"name": "Jipconomy", "json": "JipconomyApp/src/services/data.json", "db": "jipconomy_crawler/summaries.db"}
]

for p in projects:
    print(f"\n=== Analyzing {p['name']} ===")
    empty_ids = []
    
    # JSON 분석
    if os.path.exists(p['json']):
        with open(p['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                if not item.get('summary') or item['summary'].strip() == "":
                    empty_ids.append(item['id'])
                    print(f"Found empty summary in JSON: {item['id']} - {item['title']}")

    if not empty_ids:
        print("No empty summaries found in JSON.")
        continue

    # DB 정리 (재처리를 위해 삭제)
    if os.path.exists(p['db']):
        conn = sqlite3.connect(p['db'])
        cursor = conn.cursor()
        for vid in empty_ids:
            cursor.execute("DELETE FROM videos WHERE id=?", (vid,))
            print(f"Deleted from DB cache: {vid}")
        conn.commit()
        conn.close()

    # JSON 정리 (기존 데이터 유지하고 빈 것만 제거하여 크롤러가 다시 넣게 함)
    with open(p['json'], 'r', encoding='utf-8') as f:
        data = json.load(f)
    new_data = [item for item in data if item['id'] not in empty_ids]
    with open(p['json'], 'w', encoding='utf-8') as f:
        json.dump(new_data, f, ensure_ascii=False, indent=2)
    print(f"Cleaned up {len(empty_ids)} entries from {p['json']}")

