# 🚀 주식 퀀트 봇 향후 업데이트 & 유지보수 완벽 가이드

본 문서는 앞으로 새로운 기능을 추가하거나 코드를 수정할 때, **단 3단계(약 30초 소요)**로 구글 클라우드(GCP)에 최신 코드를 즉시 반영하는 표준 가이드입니다.

---

## 🔄 초고속 3단계 업데이트 워크플로우

```mermaid
flowchart LR
    A[1️⃣ AI에게 기능 수정/추가 요청] --> B[2️⃣ push_to_github.bat 더블 클릭]
    B --> C[3️⃣ GCP 터미널에서 ./update.sh 실행]
    Note over C: ⚡ 1초 만에 최신 버전으로 자동 재가동!
```

---

### 1단계: AI에게 수정 요청하기
- 저(AI)에게 채팅으로 원하는 내용을 말씀해 주세요:
  - *"새로운 기술적 지표 추가해줘"*
  - *"Gemini AI 진단 코멘트 스타일을 바꿔줘"*
  - *"새로운 스크리너 전략 추가해줘"*
- 제가 로컬 컴퓨터의 코드를 수정하고 검증을 완료합니다.

---

### 2단계: GitHub로 1초 푸시하기
- 내 컴퓨터의 `C:\Users\bosan\projects\my-vibe-app\stock_bot_project` 폴더에서:
  👉 **[`push_to_github.bat`](file:///c:/Users/bosan/projects/my-vibe-app/stock_bot_project/push_to_github.bat)** 파일을 **더블 클릭**합니다.
- 변경된 모든 코드가 GitHub 저장소로 1초 만에 자동 푸시됩니다.

---

### 3단계: 구글 클라우드 가상 컴퓨터에서 자동 반영하기
1. [Google Cloud Console](https://console.cloud.google.com/) 우측 상단의 **`[>_ Cloud Shell]`** 터미널을 엽니다.
2. 아래 명령어를 복사/붙여넣고 **엔터**를 칩니다:

```bash
gcloud compute ssh stock-bot-vm --zone=us-central1-a --command="./update.sh"
```

> ✅ **끝났습니다!** 구글 클라우드가 GitHub에서 최신 코드를 다운로드하고 봇을 백그라운드에서 즉시 자동 재시작합니다.

---

## 🛠️ 유용한 일상 관리 팁

### 1. 봇이 잘 돌아가는지 로그 확인하고 싶을 때
Cloud Shell 터미널에서:
```bash
gcloud compute ssh stock-bot-vm --zone=us-central1-a --command="tail -n 20 bot.log"
```

### 2. 단순 관심종목 추가/삭제 (코드 수정 필요 없음!)
텔레그램 앱 채팅창에서 바로 입력:
- 관심종목 추가: `/add NVDA`, `/add 카카오`
- 관심종목 삭제: `/del TSLA`
- 목록 확인: `/list`

### 3. 봇을 완전히 재부팅하고 싶을 때
```bash
gcloud compute ssh stock-bot-vm --zone=us-central1-a --command="./update.sh"
```
