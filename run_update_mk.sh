#!/bin/bash
# 서울경제TV 요약 데이터 업데이트 자동화 스크립트

# 프로젝트 루트 경로 (절대 경로 사용)
PROJECT_ROOT="/Users/kimkyungho/app01"
DATA_FILE="MKSummaryApp/src/services/data.json"

echo "--- 1. 최신 뉴스 요약 시작 (매경 월가월부) ---"
cd "$PROJECT_ROOT/mk_crawler" || exit
python3 processor.py

echo "--- 2. GitHub 업데이트 (앱 데이터 동기화) ---"
cd "$PROJECT_ROOT" || exit

# data.json 파일이 변경되었는지 확인
if git diff --quiet "$DATA_FILE"; then
    echo "데이터 변경 사항이 없습니다. (GitHub 푸시 생략)"
else
    echo "새로운 데이터 발견! GitHub에 푸시합니다..."
    git add "$DATA_FILE"
    git commit -m "Update data.json: $(date +'%Y-%m-%d %H:%M:%S')"
    # 필요한 경우 브랜치 명시 (예: git push origin main)
    git push
    echo "GitHub 푸시 완료!"
fi

echo "--- 업데이트 완료! ---"
