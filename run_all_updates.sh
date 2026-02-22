#!/bin/zsh
# 전종목 요약 데이터 업데이트 통합 자동화 스크립트

PROJECT_ROOT="/Users/kimkyungho/app01"
LOG_FILE="$PROJECT_ROOT/update_log.txt"

echo "--- 업데이트 시작: $(date +'%Y-%m-%d %H:%M:%S') ---" >> "$LOG_FILE"

# 1. 깃허브에서 최신 상태 가져오기 (멀티 디바이스 동기화)
echo "Pulling latest changes from GitHub..." >> "$LOG_FILE"
cd "$PROJECT_ROOT" || exit
git pull >> "$LOG_FILE" 2>&1

# 크롤러 목록 및 관련 데이터 파일 경로 (zsh 연관 배열)
typeset -A CRAWLERS
CRAWLERS=(
    "crawler" "SentvSummaryApp/src/services/data.json"
    "mk_crawler" "MKSummaryApp/src/services/data.json"
    "hk_global_crawler" "HKGlobalApp/src/services/data.json"
    "hk_korea_crawler" "HKKoreaApp/src/services/data.json"
    "jipconomy_crawler" "JipconomyApp/src/services/data.json"
)

for crawler_dir in "${(@k)CRAWLERS}"; do
    data_file="${CRAWLERS[$crawler_dir]}"
    echo "Processing $crawler_dir..." >> "$LOG_FILE"
    
    cd "$PROJECT_ROOT/$crawler_dir" || continue
    python3 processor.py >> "$LOG_FILE" 2>&1
    
    # 앱 간 부하 분산을 위한 대기 (30~60초)
    sleep_time=$(( 30 + RANDOM % 31 ))
    echo "Waiting $sleep_time seconds before next app..." >> "$LOG_FILE"
    sleep $sleep_time
    
    cd "$PROJECT_ROOT" || continue
    
    if git diff --quiet "$data_file"; then
        echo "$data_file: 변경 사항 없음" >> "$LOG_FILE"
    else
        echo "$data_file: 새로운 데이터 발견! 스테이징 중..." >> "$LOG_FILE"
        git add "$data_file"
    fi
done

# 변경사항이 있으면 한꺼번에 푸시
if ! git diff --cached --quiet; then
    echo "GitHub에 업데이트 푸시 중..." >> "$LOG_FILE"
    git commit -m "Auto-update all apps data: $(date +'%Y-%m-%d %H:%M:%S')"
    # SSH 환경 등이 설정되어 있어야 함
    git push >> "$LOG_FILE" 2>&1
    echo "GitHub 푸시 완료!" >> "$LOG_FILE"
else
    echo "업데이트된 데이터가 없습니다." >> "$LOG_FILE"
fi

echo "--- 업데이트 완료: $(date +'%Y-%m-%d %H:%M:%S') ---" >> "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"
