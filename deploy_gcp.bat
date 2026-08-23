@echo off
chcp 65001 > nul
echo =======================================================================
echo   🚀 Google Cloud Run (Hardened Serverless) 보안 원클릭 자동 배포
echo =======================================================================
echo.

:: 1. .env 파일에서 환경변수 로드
if exist .env (
    for /f "usebackq tokens=1,* delims==" %%a in (".env") do (
        set "line=%%a"
        if not "!line:~0,1!"=="#" (
            set "%%a=%%b"
        )
    )
)

if "%WEBHOOK_SECRET%"=="" set WEBHOOK_SECRET=stock_bot_secure_secret_token_2026

echo [1/3] GCP Cloud Run 배포 시작 (보안 & 0원 무료 최적화 설정 적용)...
echo • 리전: us-central1 (평생 무료 티어 리전)
echo • 컨테이너: Non-root 보안 실행 (appuser:10001)
echo • 네트워킹: Max Instances=2, CPU Throttling=ON (과금 100%% 차단)
echo.

call gcloud run deploy stock-quant-bot ^
    --source . ^
    --region us-central1 ^
    --allow-unauthenticated ^
    --ingress all ^
    --min-instances 0 ^
    --max-instances 2 ^
    --concurrency 40 ^
    --timeout 15s ^
    --cpu-throttling ^
    --memory 512Mi ^
    --cpu 1 ^
    --set-env-vars TELEGRAM_BOT_TOKEN=%TELEGRAM_BOT_TOKEN%,TELEGRAM_CHAT_ID=%TELEGRAM_CHAT_ID%,GEMINI_API_KEY=%GEMINI_API_KEY%,WEBHOOK_SECRET=%WEBHOOK_SECRET%

if %errorlevel% neq 0 (
    echo.
    echo ❌ 배포 중 오류가 발생했습니다. gcloud 로그인을 확인해주세요.
    echo (명령어: gcloud auth login)
    pause
    exit /b %errorlevel%
)

echo.
echo [2/3] Cloud Run 배포 URL 조회 중...
for /f "tokens=*" %%i in ('gcloud run services describe stock-quant-bot --region us-central1 --format="value(status.url)"') do set SERVICE_URL=%%i

echo.
echo ✅ 배포 성공! Cloud Run URL: %SERVICE_URL%
echo.
echo [3/3] 텔레그램 보안 웹훅(Secret Token Verification) 자동 연결 중...
curl -s "%SERVICE_URL%/set_webhook?url=%SERVICE_URL%/webhook"

echo.
echo.
echo =======================================================================
echo   🎉 프로덕션 수준의 보안 & 0원 서버리스 배포가 완료되었습니다!
echo   이제 로컬 PC를 끄셔도 24시간 365일 스마트폰 텔레그램으로 작동합니다.
echo =======================================================================
pause
