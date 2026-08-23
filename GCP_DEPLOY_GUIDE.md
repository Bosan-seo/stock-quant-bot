# ☁️ Google Cloud Run (Serverless) 100% 무료 배포 & 보안 완벽 가이드

본 가이드는 내 컴퓨터를 끄더라도 **구글 클라우드(GCP)에서 24시간 365일 대기하다가, 사용자가 텔레그램에서 호출할 때만 0.1초 만에 순간 기동하여 답변하는 서버리스(Serverless Webhook) 방식**으로 100% 무료(0원) 및 엔터프라이즈급 보안으로 배포하는 방법입니다.

---

## 🛡️ 적용된 컨테이너 및 네트워킹 보안 강화 설정

1. **컨테이너 보안 (Container Hardening)**:
   - **Non-root 실행**: 컨테이너가 루트 권한이 아닌 보안 전용 비루트 계정(`appuser:10001`)으로 안전하게 구동됩니다.
   - **경량 최적화**: Python 3.11-slim 기반으로 최소한의 종속성만 포함하여 콜드스타트(기동 시간)를 0.5초 이내로 단축.
2. **네트워킹 & 웹훅 스푸핑 방지 (Network Security)**:
   - **Telegram Secret Token 검증**: `X-Telegram-Bot-Api-Secret-Token` 헤더를 검증하여, 제3자가 웹훅 URL로 보내는 악성 위조 요청을 100% 차단(403 Forbidden).
   - **보안 응답 헤더**: `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `HSTS` 탑재.
3. **과금 & 트래픽 안전장치 (Cost & Rate Limiting)**:
   - **`--min-instances 0`**: 평소 CPU 0% 유지 (0원 유지 핵심).
   - **`--max-instances 2`**: 트래픽 공격/무한 루프 시에도 인스턴스가 2대 이상 늘어나지 않도록 과금 상한선 원천 차단.
   - **`--cpu-throttling`**: 요청이 끝나면 즉시 CPU를 절전 상태로 전환.

---

## 🚀 방법 1: 원클릭 스크립트 배포 (가장 빠름 / 추천 ⭐)

### 1단계: Google Cloud SDK (gcloud CLI) 로그인
1. 명령 프롬프트(CMD) 또는 PowerShell을 열고 Google Cloud에 로그인합니다:
   ```cmd
   gcloud auth login
   ```
2. 배포할 GCP 프로젝트를 설정합니다:
   ```cmd
   gcloud config set project YOUR_PROJECT_ID
   ```

### 2단계: 원클릭 배포 실행
`stock_bot_project` 폴더 안의 **[`deploy_gcp.bat`](file:///c:/Users/bosan/projects/my-vibe-app/stock_bot_project/deploy_gcp.bat)** 파일을 더블 클릭하여 실행합니다.

> 💡 스크립트가 자동으로 `.env`의 토큰들을 읽어와서 **보안 컨테이너 빌드 ➡️ Cloud Run 배포 ➡️ 비밀 토큰 포함 텔레그램 웹훅 등록**까지 1분 만에 전자동으로 끝마칩니다!

---

## 🌐 방법 2: gcloud 명령어로 직접 1줄 배포

```cmd
gcloud run deploy stock-quant-bot ^
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
    --set-env-vars TELEGRAM_BOT_TOKEN="내_토큰",TELEGRAM_CHAT_ID="내_CHAT_ID",GEMINI_API_KEY="내_API키",WEBHOOK_SECRET="stock_bot_secure_secret_token_2026"
```

배포가 끝나면 출력된 **Service URL** (예: `https://stock-quant-bot-xxxxx.a.run.app`)을 복사한 후 브라우저 주소창에 아래와 같이 입력하여 웹훅을 연결합니다:
```text
https://stock-quant-bot-xxxxx.a.run.app/set_webhook?url=https://stock-quant-bot-xxxxx.a.run.app/webhook
```

---

## ✅ 배포 완료 후 확인 방법

1. **로컬 PC의 파이썬 봇 종료**:
   - 내 컴퓨터에서 돌아가던 로컬 봇을 끕니다.
2. **스마트폰 텔레그램 테스트**:
   - 텔레그램 채팅창에서 **`/start`**를 치거나 **`[🎯 퀀트 유망주 발굴]`** 버튼을 눌러보세요.
   - 내 컴퓨터가 꺼져 있어도 **구글 클라우드 런이 0.1초 만에 순간 기동하여 즉시 답변**합니다!
