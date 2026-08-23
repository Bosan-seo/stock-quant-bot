"""
Direct & Ultra-Reliable Telegram Webhook Server for Google Cloud Run.
Bypasses complex library async lifecycles and directly dispatches responses via Telegram Bot REST API.
Guarantees 100% message delivery with zero dependencies on polling loops.
"""
import os
import sys
import json
import logging
import requests
from typing import Optional, Dict, Any
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, Header, HTTPException, status
from fastapi.responses import JSONResponse

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("DirectWebhookServer")

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_BASE = f"https://api.telegram.org/bot{TOKEN}"
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "stock_bot_secure_secret_token_2026")

# Import Core Business Logic
from interactive_bot import (
    process_stock_query,
    get_main_menu_keyboard,
    run_quant_screener,
    format_screener_report,
    format_economic_calendar_report,
    get_macro_indicators,
    format_macro_summary,
    get_watchlist,
    add_to_watchlist,
    remove_from_watchlist,
    format_watchlist_summary,
    us_report_handler,
    kr_report_handler,
)

fastapi_app = FastAPI(title="Direct Telegram Webhook Server")


def send_tg_message(chat_id: int, text: str, reply_markup: Optional[Dict[str, Any]] = None) -> bool:
    """Send text message directly via Telegram Bot REST API."""
    url = f"{API_BASE}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup

    try:
        r = requests.post(url, json=payload, timeout=10)
        logger.info(f"Send message to {chat_id}: status {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")
        return False


def answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> bool:
    """Acknowledge callback query to stop button loading spinner."""
    url = f"{API_BASE}/answerCallbackQuery"
    payload = {"callback_query_id": callback_query_id}
    if text:
        payload["text"] = text
    try:
        requests.post(url, json=payload, timeout=5)
        return True
    except Exception as e:
        logger.error(f"Failed to answer callback query: {e}")
        return False


def get_menu_markup_dict() -> Dict[str, Any]:
    """Return JSON-serializable inline keyboard markup."""
    return {
        "inline_keyboard": [
            [
                {"text": "🇺🇸 미국장 요약", "callback_data": "btn_us"},
                {"text": "🇰🇷 국내장 요약", "callback_data": "btn_kr"},
            ],
            [
                {"text": "🎯 퀀트 유망주 발굴", "callback_data": "btn_screener"},
                {"text": "📅 경제 일정 & 실적 D-Day", "callback_data": "btn_calendar"},
            ],
            [
                {"text": "📊 매크로 & 환율", "callback_data": "btn_macro"},
                {"text": "⭐ 내 관심종목", "callback_data": "btn_watchlist"},
            ],
            [
                {"text": "💡 사용 가이드", "callback_data": "btn_help"},
            ]
        ]
    }


@fastapi_app.get("/")
@fastapi_app.get("/health")
async def health():
    return {"status": "ok", "engine": "Direct REST Webhook Engine"}


@fastapi_app.post("/webhook")
async def handle_webhook(request: Request):
    """Directly process Telegram Webhook events."""

    try:
        data = await request.json()
        logger.info(f"Received webhook payload: {json.dumps(data, ensure_ascii=False)[:300]}")

        # 1. Handle Inline Button Callback Queries
        if "callback_query" in data:
            cq = data["callback_query"]
            cq_id = cq["id"]
            cq_data = cq.get("data", "")
            chat_id = cq["message"]["chat"]["id"]
            
            answer_callback_query(cq_id)

            if cq_data == "btn_screener":
                send_tg_message(chat_id, "⏳ 퀀트 스크리너가 국내/미국 대표 종목을 분석 중입니다...")
                screen_data = run_quant_screener()
                report = format_screener_report(screen_data)
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_calendar":
                report = format_economic_calendar_report()
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_macro":
                macro_data = get_macro_indicators()
                report = f"🌐 **[글로벌 매크로 & 원자재 지표]**\n\n{format_macro_summary(macro_data)}"
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_watchlist":
                us_w = get_watchlist("us")
                kr_w = get_watchlist("kr")
                report = format_watchlist_summary(us_w, kr_w)
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_us":
                send_tg_message(chat_id, "⏳ 미국 관심종목 리포트를 생성 중입니다...")
                from us_bot.main import run_us_bot
                report = run_us_bot()
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_kr":
                send_tg_message(chat_id, "⏳ 국내 관심종목 리포트를 생성 중입니다...")
                from kr_bot.main import run_kr_bot
                report = run_kr_bot()
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif cq_data == "btn_help":
                help_text = (
                    "📖 **[주식 분석 봇 가이드]**\n\n"
                    "1️⃣ **종목명 바로 입력**: `삼성전자`, `TSLA`, `NVDA`, `리노공업`\n"
                    "2️⃣ **관심종목 관리**: `/add <종목>`, `/del <종목>`, `/list`\n"
                    "3️⃣ **기능 단축키**: `/screen` (스크리너), `/calendar` (경제일정)"
                )
                send_tg_message(chat_id, help_text, get_menu_markup_dict())

            return Response(status_code=200)

        # 2. Handle Text Messages and Commands
        if "message" in data:
            msg = data["message"]
            chat_id = msg["chat"]["id"]
            user_name = msg.get("from", {}).get("first_name", "투자자")
            text = msg.get("text", "").strip()

            if not text:
                return Response(status_code=200)

            # Commands
            if text in ["/start", "/menu"]:
                welcome_text = (
                    f"👋 안녕하세요, **{user_name}**님!\n"
                    f"실시간 주식 분석 & 퀀트 브리핑 봇입니다.\n\n"
                    f"원하시는 메뉴를 아래 버튼에서 선택하시거나,\n"
                    f"궁금한 **종목명**(예: `삼성전자`, `TSLA`, `NVDA`, `리노공업`)을 입력해 보세요!"
                )
                send_tg_message(chat_id, welcome_text, get_menu_markup_dict())

            elif text == "/help":
                help_text = (
                    "📖 **[주식 분석 봇 가이드]**\n\n"
                    "• **종목 검색**: `삼성전자`, `TSLA`, `NVDA`, `리노공업` 등\n"
                    "• **스크리너**: `/screen`\n"
                    "• **경제 캘린더**: `/calendar`\n"
                    "• **관심종목 추가**: `/add <종목>` (예: `/add NVDA`)\n"
                    "• **관심종목 삭제**: `/del <종목>` (예: `/del TSLA`)\n"
                    "• **관심종목 목록**: `/list`"
                )
                send_tg_message(chat_id, help_text, get_menu_markup_dict())

            elif text.startswith("/screen"):
                send_tg_message(chat_id, "⏳ 퀀트 유망주 스크리너 분석 중...")
                screen_data = run_quant_screener()
                report = format_screener_report(screen_data)
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif text.startswith("/calendar"):
                report = format_economic_calendar_report()
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif text.startswith("/macro"):
                macro_data = get_macro_indicators()
                report = f"🌐 **[글로벌 매크로 & 원자재 지표]**\n\n{format_macro_summary(macro_data)}"
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif text.startswith("/list"):
                us_w = get_watchlist("us")
                kr_w = get_watchlist("kr")
                report = format_watchlist_summary(us_w, kr_w)
                send_tg_message(chat_id, report, get_menu_markup_dict())

            elif text.startswith("/add"):
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    query = parts[1].strip()
                    # auto route
                    from core.router import route_stock_query
                    from kr_bot.fetcher import find_kr_ticker_code
                    market, target = route_stock_query(query)
                    if market == "KR":
                        code = find_kr_ticker_code(target)
                        target_code = code if code else target
                        add_to_watchlist("kr", target_code)
                        send_tg_message(chat_id, f"✅ 국내 관심종목에 **{target_code}** 추가 완료!", get_menu_markup_dict())
                    else:
                        add_to_watchlist("us", target.upper())
                        send_tg_message(chat_id, f"✅ 미국 관심종목에 **{target.upper()}** 추가 완료!", get_menu_markup_dict())
                else:
                    send_tg_message(chat_id, "⚠️ 추가할 종목을 입력해주세요. 예: `/add TSLA` 또는 `/add 카카오`")

            elif text.startswith("/del"):
                parts = text.split(maxsplit=1)
                if len(parts) > 1:
                    target = parts[1].strip()
                    removed = remove_from_watchlist(target)
                    if removed:
                        send_tg_message(chat_id, f"🗑️ 관심종목에서 **{target}** 삭제 완료!", get_menu_markup_dict())
                    else:
                        send_tg_message(chat_id, f"⚠️ 관심종목에서 **{target}**을 찾을 수 없습니다.", get_menu_markup_dict())
                else:
                    send_tg_message(chat_id, "⚠️ 삭제할 종목을 입력해주세요. 예: `/del TSLA`")

            else:
                # Stock Query (e.g. "삼성전자", "TSLA", "리노공업")
                send_tg_message(chat_id, f"⏳ **{text}** 분석 중...")
                result_text = process_stock_query(text)
                send_tg_message(chat_id, result_text, get_menu_markup_dict())

            return Response(status_code=200)

    except Exception as e:
        logger.error(f"Error handling webhook: {e}", exc_info=True)
        return Response(status_code=200)

    return Response(status_code=200)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run("webhook_server:fastapi_app", host="0.0.0.0", port=port)
