import json
import os
import sqlite3

apps = [
    {"name": "HKKorea", "json": "HKKoreaApp/src/services/data.json", "db": "hk_korea_crawler/summaries.db"},
    {"name": "Jipconomy", "json": "JipconomyApp/src/services/data.json", "db": "jipconomy_crawler/summaries.db"},
    {"name": "MK", "json": "MKSummaryApp/src/services/data.json", "db": "mk_crawler/summaries.db"},
    {"name": "HKGlobal", "json": "HKGlobalApp/src/services/data.json", "db": "hk_global_crawler/summaries.db"},
    {"name": "Sentv", "json": "SentvSummaryApp/src/services/data.json", "db": "crawler/summaries.db"}
]

for app in apps:
    if os.path.exists(app['json']):
        with open(app['json'], 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        empty_ids = [item['id'] for item in data if not item.get('summary') or item['summary'].strip() == ""]
        
        if empty_ids:
            print(f"{app['name']}: Found {len(empty_ids)} empty summaries. Cleaning...")
            # Clean JSON
            clean_data = [item for item in data if item['id'] not in empty_ids]
            with open(app['json'], 'w', encoding='utf-8') as f:
                json.dump(clean_data, f, ensure_ascii=False, indent=2)
            
            # Clean DB
            if os.path.exists(app['db']):
                conn = sqlite3.connect(app['db'])
                cursor = conn.cursor()
                for vid in empty_ids:
                    cursor.execute("DELETE FROM videos WHERE id=?", (vid,))
                conn.commit()
                conn.close()
        else:
            print(f"{app['name']}: Clean.")
