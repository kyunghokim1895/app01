#!/bin/bash
# 서울경제TV 요약 데이터 업데이트 자동화 스크립트

echo "--- 1. 최신 뉴스 요약 시작 (3개월치) ---"
cd /Users/kimkyungho/app01/crawler
python3 processor.py

echo "--- 2. 앱 데이터 동기화 (로컬 빌드용) ---"
cp /Users/kimkyungho/app01/SentvSummaryApp/src/services/data.json /Users/kimkyungho/app01/SentvSummaryApp/src/services/data.json

echo "--- 업데이트 완료! ---"
echo "TIP: 원격 자동 업데이트를 사용하신다면 생성된 'data.json' 파일을 GitHub 등에 업로드해 주세요."
