@echo off
setlocal enabledelayedexpansion

:: 3개 프로젝트 최신 상태 동기화 스크립트 (Windows용)
:: 사용자 환경에 맞춰 폴더 경로를 수정해주세요.

:: 기본 작업 경로 (예: C:\Users\kimkyungho)
set "BASE_DIR=%USERPROFILE%"

:: 프로젝트 폴더 목록
set "PROJECTS=app01 solo-preneur MentalCoach"

echo --- 프로젝트 동기화 시작: %date% %time% ---

for %%p in (%PROJECTS%) do (
    set "TARGET_DIR=%BASE_DIR%\%%p"
    if exist "!TARGET_DIR!" (
        echo.
        echo [ %%p ] 업데이트 중...
        cd /d "!TARGET_DIR!"
        git pull
    ) else (
        echo.
        echo [ %%p ] 폴더를 찾을 수 없습니다: !TARGET_DIR!
        echo (이 컴퓨터의 실제 경로에 맞춰 .bat 파일을 편집기로 수정해주세요.)
    )
)

echo.
echo --- 모든 프로젝트 동기화 완료! ---
pause
