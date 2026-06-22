#!/bin/zsh
# 전종목 요약 데이터 업데이트 통합 자동화 스크립트

# 스크립트 위치를 기준으로 프로젝트 루트 설정 (경로 하드코딩 제거)
PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
# mac 로컬 실행 시엔 기존 프레임워크 파이썬, CI(Linux) 등에선 PATH의 python3 사용.
# 환경변수 PYTHON_BIN으로 덮어쓸 수 있음.
if [[ -z "$PYTHON_BIN" ]]; then
    if [[ -x "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" ]]; then
        PYTHON_BIN="/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    else
        PYTHON_BIN="python3"
    fi
fi
LOG_FILE="$PROJECT_ROOT/update_log.txt"

echo "--- 업데이트 시작: $(date +'%Y-%m-%d %H:%M:%S') ---" | tee -a "$LOG_FILE"

# 스크립트 자체가 caffeinate 하에서 실행되도록 보장 (잠자기 방지)
if [[ "$1" != "--child" ]]; then
    if command -v caffeinate >/dev/null 2>&1; then
        echo "Starting with caffeinate (system sleep prevention active)..." | tee -a "$LOG_FILE"
        caffeinate -i "$0" --child "$@"
    else
        # Linux/CI 등 caffeinate가 없는 환경에서는 그대로 실행
        "$0" --child "$@"
    fi
    exit $?
fi
shift # --child 인자 제거

# 1. 깃허브에서 최신 상태 가져오기 (멀티 디바이스 동기화)
# GitHub Actions 환경에서는 워크플로우에서 직접 관리하므로 건너뜁니다.
if [[ -z "$GITHUB_ACTIONS" ]] && [[ "$*" != *"--no-sync"* ]]; then
    echo "Pulling latest changes from GitHub (timeout 30s)..." | tee -a "$LOG_FILE"
    cd "$PROJECT_ROOT" || exit
    git config pull.rebase true
    # 터미널 프롬프트 방지 및 타임아웃 설정
    if export GIT_TERMINAL_PROMPT=0; git pull --no-edit origin $(git rev-parse --abbrev-ref HEAD) >> "$LOG_FILE" 2>&1; then
        echo "Pull successful." | tee -a "$LOG_FILE"
    else
        echo "Pull failed or skipped (no credentials?). Continuing with local version..." | tee -a "$LOG_FILE"
    fi
fi

# 크롤러 목록 및 관련 데이터 파일 경로 (zsh 연관 배열)
typeset -A CRAWLERS
CRAWLERS=(
    "crawler" "SentvSummaryApp/src/services/data.json"
    "mk_crawler" "MKSummaryApp/src/services/data.json"
    "hk_global_crawler" "HKGlobalApp/src/services/data.json"
    "hk_korea_crawler" "HKKoreaApp/src/services/data.json"
    "jipconomy_crawler" "JipconomyApp/src/services/data.json"
    "hktv_global_crawler" "HKTVGlobalApp/src/services/data.json"
)

# 특정 앱 하나만 실행할 경우 (인자값 확인)
TARGET_APP=""
if [[ "$1" != "" ]]; then
    TARGET_APP="$1"
    echo "Target app specified: $TARGET_APP" | tee -a "$LOG_FILE"
fi

for crawler_dir in "${(@k)CRAWLERS}"; do
    if [[ "$TARGET_APP" != "" && "$crawler_dir" != "$TARGET_APP" ]]; then
        continue
    fi
    
    data_file="${CRAWLERS[$crawler_dir]}"
    echo "Processing $crawler_dir..." | tee -a "$LOG_FILE"
    
    cd "$PROJECT_ROOT/$crawler_dir" || continue
    "$PYTHON_BIN" processor.py 2>&1 | tee -a "$LOG_FILE"
    
    # 병렬 실행 시에는 앱 간 대기 불필요, 단일 실행 시에도 다음 앱이 없으면 대기 불필요
    if [[ "$TARGET_APP" == "" ]]; then
        # 다음 앱 처리 전 짧은 대기 (Gemini API 안정화)
        sleep_time=$(( 5 + RANDOM % 6 ))
        echo "Waiting $sleep_time seconds before next app..." | tee -a "$LOG_FILE"
        sleep $sleep_time
    fi
    
    cd "$PROJECT_ROOT" || continue
    
    if git diff --quiet "$data_file"; then
        echo "$data_file: 변경 사항 없음" | tee -a "$LOG_FILE"
    else
        echo "$data_file: 새로운 데이터 발견! 스테이징 중..." | tee -a "$LOG_FILE"
        git add "$data_file"
    fi
done

# 변경사항이 있으면 한꺼번에 푸시 (GitHub Actions 환경이 아닐 때만)
if [[ -z "$GITHUB_ACTIONS" ]] && ! git diff --cached --quiet; then
    echo "GitHub에 업데이트 푸시 중..." | tee -a "$LOG_FILE"
    git commit -m "Auto-update all apps data: $(date +'%Y-%m-%d %H:%M:%S')"
    # SSH 환경 등이 설정되어 있어야 함
    git push >> "$LOG_FILE" 2>&1
    echo "GitHub 푸시 완료!" | tee -a "$LOG_FILE"
elif [[ -n "$GITHUB_ACTIONS" ]]; then
    echo "GitHub Actions detected. Skipping internal commit/push as it is handled by the workflow." | tee -a "$LOG_FILE"
else
    echo "업데이트된 데이터가 없습니다." | tee -a "$LOG_FILE"
fi

echo "Cleaning up temporary files..." | tee -a "$LOG_FILE"

echo "--- 모든 앱 업데이트 프로세스 완료: $(date +'%Y-%m-%d %H:%M:%S') ---" | tee -a "$LOG_FILE"

echo "--- 업데이트 완료: $(date +'%Y-%m-%d %H:%M:%S') ---" | tee -a "$LOG_FILE"
echo "-------------------------------------------" >> "$LOG_FILE"
