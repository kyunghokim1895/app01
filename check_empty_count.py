import json
import os

projects = [
    {"name": "HKKorea", "json": "HKKoreaApp/src/services/data.json"},
    {"name": "HKGlobal", "json": "HKGlobalApp/src/services/data.json"},
    {"name": "Jipconomy", "json": "JipconomyApp/src/services/data.json"},
    {"name": "MK", "json": "MKSummaryApp/src/services/data.json"}
]

for p in projects:
    if os.path.exists(p['json']):
        with open(p['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
            empty = [item['id'] for item in data if not item.get('summary') or item['summary'].strip() == ""]
            print(f"{p['name']}: Total {len(data)}, Empty {len(empty)}")
