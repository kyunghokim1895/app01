import os
import re

crawlers = [
    "/Users/kimkyungho/app01/hk_korea_crawler/processor.py",
    "/Users/kimkyungho/app01/hk_global_crawler/processor.py",
    "/Users/kimkyungho/app01/jipconomy_crawler/processor.py"
]

for crawler_path in crawlers:
    if os.path.exists(crawler_path):
        with open(crawler_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. new_entries + existing_data 로 정렬 수정
        # (기존에 existing_data + new_entries로 되어 있는 부분을 찾아서 바꿉니다)
        pattern = r"new_entries\s*\+\s*existing_data"
        if "existing_data + new_entries" in content:
            content = content.replace("existing_data + new_entries", "new_entries + existing_data")
            print(f"Fixed ordering logic in {crawler_path}")
        elif "new_entries + existing_data" in content:
            print(f"Ordering logic already correct in {crawler_path}")
        else:
            print(f"Warning: Could not find merge logic in {crawler_path}")

        # 2. timedelta(days=14) -> timedelta(days=30) 설정
        if "timedelta(days=14)" in content:
            content = content.replace("timedelta(days=14)", "timedelta(days=30)")
            print(f"Updated collection range to 30 days in {crawler_path}")

        with open(crawler_path, 'w', encoding='utf-8') as f:
            f.write(content)
