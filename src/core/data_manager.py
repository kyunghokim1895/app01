import os
import sqlite3
import json

def init_db(db_path):
    os.makedirs(os.path.dirname(db_path), exist_ok=True) if os.path.dirname(db_path) else None
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id TEXT PRIMARY KEY,
            title TEXT,
            summary TEXT,
            summaryList TEXT,
            keywords TEXT,
            publishedAt TEXT,
            videoUrl TEXT
        )
    ''')
    conn.commit()
    conn.close()

def load_json_data(json_path):
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_json_data(json_path, data):
    os.makedirs(os.path.dirname(json_path), exist_ok=True) if os.path.dirname(json_path) else None
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def sync_db_to_json(db_path, json_path):
    if not os.path.exists(db_path): return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, summary, summaryList, keywords, publishedAt, videoUrl FROM videos WHERE summary IS NOT NULL AND summary != ''")
    rows = cursor.fetchall()
    
    db_data = []
    for row in rows:
        try:
            db_data.append({
                "id": row[0], "title": row[1], "summary": row[2],
                "summaryList": json.loads(row[3]), "keywords": json.loads(row[4]),
                "publishedAt": row[5], "videoUrl": row[6]
            })
        except Exception: continue
    conn.close()
    
    existing_data = load_json_data(json_path)
    all_data = db_data + existing_data
    unique_data = {item['id']: item for item in all_data}.values()
    sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
    
    save_json_data(json_path, sorted_data)
    return {item['id'] for item in sorted_data}

def save_video_to_db(db_path, video_id, title, analysis, published_at, video_url):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO videos VALUES (?,?,?,?,?,?,?)", (
        video_id, title, analysis['summary'],
        json.dumps(analysis['summaryList'], ensure_ascii=False),
        json.dumps(analysis['keywords'], ensure_ascii=False),
        published_at, video_url
    ))
    conn.commit()
    conn.close()

def update_incremental_json(json_path, new_item):
    current_data = load_json_data(json_path)
    all_data = [new_item] + current_data
    unique_data = {item['id']: item for item in all_data}.values()
    sorted_data = sorted(unique_data, key=lambda x: x.get('publishedAt', ''), reverse=True)
    save_json_data(json_path, sorted_data)
