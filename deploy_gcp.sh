#!/bin/bash
set -e

echo "======================================================================="
echo "  🚀 Google Cloud Run (Hardened Serverless) 보안 원클릭 자동 배포"
echo "======================================================================="

# Load .env
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

WEBHOOK_SECRET=${WEBHOOK_SECRET:-"stock_bot_secure_secret_token_2026"}

echo "[1/3] GCP Cloud Run 배포 시작 (us-central1, Hardened Security)..."
gcloud run deploy stock-quant-bot \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --ingress all \
    --min-instances 0 \
    --max-instances 2 \
    --concurrency 40 \
    --timeout 15s \
    --cpu-throttling \
    --memory 512Mi \
    --cpu 1 \
    --set-env-vars TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN",TELEGRAM_CHAT_ID="$TELEGRAM_CHAT_ID",GEMINI_API_KEY="$GEMINI_API_KEY",WEBHOOK_SECRET="$WEBHOOK_SECRET"

echo "[2/3] 서비스 URL 조회..."
SERVICE_URL=$(gcloud run services describe stock-quant-bot --region us-central1 --format='value(status.url)')

echo "✅ 배포 완료: $SERVICE_URL"
echo "[3/3] 텔레그램 보안 웹훅 등록..."
curl -s "$SERVICE_URL/set_webhook?url=$SERVICE_URL/webhook"

echo ""
echo "🎉 서버리스 배포 완료! PC를 끄셔도 텔레그램으로 언제든 동작합니다."
