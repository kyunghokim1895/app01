@echo off
setlocal enabledelayedexpansion

:: 프로젝트 루트 경로 설정 (스크립트 위치 기준)
set "PROJECT_ROOT=%~dp0"
set "LOG_FILE=%PROJECT_ROOT%update_log.txt"

echo --- 업데이트 시작: %date% %time% --- >> "%LOG_FILE%"

:: 1. 깃허브에서 최신 상태 가져오기 (멀티 디바이스 동기화)
echo Pulling latest changes from GitHub... >> "%LOG_FILE%"
cd /d "%PROJECT_ROOT%"
git pull >> "%LOG_FILE%" 2>&1

:: 크롤러 목록 설정
set "CRAWLERS=crawler mk_crawler hk_global_crawler hk_korea_crawler jipconomy_crawler"
set "DATA_FILES=SentvSummaryApp/src/services/data.json MKSummaryApp/src/services/data.json HKGlobalApp/src/services/data.json HKKoreaApp/src/services/data.json JipconomyApp/src/services/data.json"

:: 각 크롤러 순회
for %%d in (%CRAWLERS%) do (
    echo Processing %%d... >> "%LOG_FILE%"
    cd /d "%PROJECT_ROOT%%%d"
    
    :: 윈도우에서는 python 또는 python3 명령어를 모두 시도
    python --version >nul 2>&1
    if !errorlevel! equ 0 (
        python processor.py >> "%LOG_FILE%" 2>&1
    ) else (
        python3 processor.py >> "%LOG_FILE%" 2>&1
    )
    
    :: 앱 간 부하 분산을 위한 대기 (30~60초)
    set /a "sleep_time=!random! %% 31 + 30"
    echo Waiting !sleep_time! seconds before next app... >> "%LOG_FILE%"
    timeout /t !sleep_time! /nobreak >nul
)

:: 변경사항 확인 및 푸시
cd /d "%PROJECT_ROOT%"
git add .
git commit -m "Auto-update all apps data (Windows): %date% %time%" >> "%LOG_FILE%" 2>&1
if !errorlevel! equ 0 (
    echo GitHub에 업데이트 푸시 중... >> "%LOG_FILE%"
    git push >> "%LOG_FILE%" 2>&1
    echo GitHub 푸시 완료! >> "%LOG_FILE%"
) else (
    echo 업데이트된 데이터가 없습니다. >> "%LOG_FILE%"
)

echo --- 업데이트 완료: %date% %time% --- >> "%LOG_FILE%"
echo ------------------------------------------- >> "%LOG_FILE%"
pause
