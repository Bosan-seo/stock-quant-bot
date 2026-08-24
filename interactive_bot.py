"""
Interactive Telegram Stock Quant Analysis Bot (Production Stable Version).
Features:
  - Smart Query Routing (Zero-collision US/KRX stock lookup)
  - 3-Strategy Quant Screener (SMA20 Breakout, Oversold Rebound, Value)
  - Macro & Earnings D-Day Calendar
  - Gemini AI 3-Line Comprehensive Quant Diagnosis
  - Resilient Message Delivery (Auto-chunking >3800 chars & Markdown parse-error fallback)
"""
import os
import sys
import logging
from datetime import datetime
from typing import List, Optional

# Ensure standard output streams support UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from core.macro import get_macro_indicators, format_macro_summary, get_single_macro_indicator
from core.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist, format_watchlist_summary
from core.router import route_stock_query
from core.screener import run_quant_screener, format_screener_report
from core.calendar import format_economic_calendar_report
from us_bot.main import analyze_us_stock, DEFAULT_WATCHLIST as US_DEFAULT_WATCHLIST
from kr_bot.main import analyze_kr_stock, DEFAULT_KR_WATCHLIST
from kr_bot.fetcher import find_kr_ticker_code

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
for logger_name in ["pykrx", "yfinance", "urllib3", "httpx", "httpcore"]:
    logging.getLogger(logger_name).setLevel(logging.ERROR)

logger = logging.getLogger("InteractiveBot")


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Return inline keyboard buttons for main actions."""
    keyboard = [
        [
            InlineKeyboardButton("🇺🇸 미국장 요약", callback_data="btn_us"),
            InlineKeyboardButton("🇰🇷 국내장 요약", callback_data="btn_kr"),
        ],
        [
            InlineKeyboardButton("🎯 퀀트 유망주 발굴", callback_data="btn_screener"),
            InlineKeyboardButton("📅 경제 일정 & 실적 D-Day", callback_data="btn_calendar"),
        ],
        [
            InlineKeyboardButton("📊 매크로 & 환율", callback_data="btn_macro"),
            InlineKeyboardButton("⭐ 내 관심종목", callback_data="btn_watchlist"),
        ],
        [
            InlineKeyboardButton("💡 사용 가이드", callback_data="btn_help"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def split_text_into_chunks(text: str, max_chars: int = 3800) -> List[str]:
    """Split long text into clean chunks at line breaks to avoid Telegram 4096-char truncation."""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    current_chunk = []
    current_length = 0

    lines = text.split("\n")
    for line in lines:
        if current_length + len(line) + 1 > max_chars and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_length = len(line)
        else:
            current_chunk.append(line)
            current_length += len(line) + 1

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


async def safe_send_or_edit(
    target_msg,
    text: str,
    reply_markup: Optional[InlineKeyboardMarkup] = None,
    status_msg = None
) -> None:
    """
    Safely send or edit Telegram messages with:
      1. Automatic chunking for long messages (>3800 chars)
      2. Markdown parse error fallback to plain text (never cut off or drop)
    """
    chunks = split_text_into_chunks(text, max_chars=3800)

    for idx, chunk in enumerate(chunks):
        is_last = (idx == len(chunks) - 1)
        markup = reply_markup if is_last else None

        # Try editing first status message if provided
        if idx == 0 and status_msg:
            try:
                await status_msg.edit_text(chunk, reply_markup=markup, parse_mode="Markdown")
                continue
            except Exception as e:
                logger.debug(f"Markdown edit failed ({e}), retrying as plain text...")
                try:
                    await status_msg.edit_text(chunk, reply_markup=markup, parse_mode=None)
                    continue
                except Exception as e2:
                    logger.debug(f"Plain text edit failed ({e2}), falling back to new reply.")

        # Send as new message
        try:
            await target_msg.reply_text(chunk, reply_markup=markup, parse_mode="Markdown")
        except Exception as e:
            logger.debug(f"Markdown send failed ({e}), falling back to plain text...")
            try:
                await target_msg.reply_text(chunk, reply_markup=markup, parse_mode=None)
            except Exception as e_final:
                logger.error(f"Failed to send message chunk: {e_final}")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message with interactive inline buttons."""
    user_name = update.effective_user.first_name if update.effective_user else "투자자"
    welcome_text = (
        f"👋 안녕하세요, **{user_name}**님!\n"
        f"실시간 주식 분석 & 퀀트 브리핑 봇입니다.\n\n"
        f"원하시는 메뉴를 아래 버튼에서 선택하시거나,\n"
        f"궁금한 **종목명**(예: `삼성전자`, `TSLA`, `카카오`, `NVDA`, `리노공업`)을 채팅창에 바로 입력해 보세요!"
    )
    if update.message:
        await safe_send_or_edit(update.message, welcome_text, get_main_menu_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message."""
    help_text = (
        "📖 **[주식 분석 봇 종합 가이드]**\n\n"
        "1️⃣ **원터치 메뉴 버튼**\n"
        "• `🇺🇸 미국장 요약` / `🇰🇷 국내장 요약` : 관심종목 퀀트 데일리 브리핑\n"
        "• `🎯 퀀트 유망주 발굴` : 20일선 돌파 & 낙폭과대 반등주 Top 5 스크리너\n"
        "• `📅 경제 일정 & 실적 D-Day` : FOMC, CPI 및 관심종목 어닝 디데이\n"
        "• `📊 매크로 & 환율` : VIX, 금리, 유가, 원달러, 엔원 환율\n\n"
        "2️⃣ **실시간 종목 즉시 분석 (AI 퀀트 총평)**\n"
        "• 채팅창에 종목명이나 티커를 그냥 입력하시면 3줄 AI 진단과 함께 리포트가 전송됩니다!\n"
        "  - 미국 주식: `AAPL`, `TSLA`, `NVDA`, `MSFT`, `ON`, `OPEN` 등\n"
        "  - 국내 주식: `삼성전자`, `SK하이닉스`, `005930`, `리노공업`, `SB성보` 등\n\n"
        "3️⃣ **관심종목 관리**\n"
        "• `/add <종목>` : 관심종목에 추가\n"
        "• `/del <종목>` : 관심종목에서 삭제\n"
        "• `/list` : 현재 등록된 관심종목 보기\n\n"
        "4️⃣ **단축 명령어 목록**\n"
        "• `/menu` : 메인 메뉴 버튼 호출\n"
        "• `/screen` : 퀀트 유망주 실시간 스크리너\n"
        "• `/calendar` : 경제 캘린더 & 실적 D-Day\n"
        "• `/us <티커>` / `/kr <종목>` : 특정 종목 직통 분석"
    )
    if update.message:
        await safe_send_or_edit(update.message, help_text, get_main_menu_keyboard())


async def watchlist_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show current watchlist."""
    us_watchlist = get_watchlist("us")
    kr_watchlist = get_watchlist("kr")
    summary = format_watchlist_summary(us_watchlist, kr_watchlist)
    target = update.message or (update.callback_query.message if update.callback_query else None)
    if target:
        await safe_send_or_edit(target, summary, get_main_menu_keyboard())


async def add_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /add <ticker/name> command."""
    if not update.message:
        return
    if not context.args:
        await safe_send_or_edit(
            update.message,
            "⚠️ 추가할 종목명 또는 티커를 입력해주세요.\n예시:\n• 미국 주식: `/add TSLA`\n• 국내 주식: `/add 카카오` 또는 `/add 005930`",
            get_main_menu_keyboard()
        )
        return

    query = " ".join(context.args).strip()
    market, target = route_stock_query(query)

    if market == "KR":
        kr_code = find_kr_ticker_code(target)
        target_code = kr_code if kr_code else target
        success, msg = add_to_watchlist("kr", target_code)
    else:
        success, msg = add_to_watchlist("us", target.upper())

    reply_text = msg
    if success:
        reply_text += f"\n\n{format_watchlist_summary()}"

    await safe_send_or_edit(update.message, reply_text, get_main_menu_keyboard())


async def del_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /del <ticker/name> command."""
    if not update.message:
        return
    if not context.args:
        await safe_send_or_edit(
            update.message,
            "⚠️ 삭제할 종목명 또는 티커를 입력해주세요.\n예시: `/del TSLA` 또는 `/del 삼성전자`",
            get_main_menu_keyboard()
        )
        return

    query = " ".join(context.args)
    success, msg = remove_from_watchlist(query)
    reply_text = msg
    if success:
        reply_text += f"\n\n{format_watchlist_summary()}"

    await safe_send_or_edit(update.message, reply_text, get_main_menu_keyboard())


async def us_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send US market report or analyze specific US stock if args provided."""
    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if not target_message:
        return

    if context.args:
        query_str = " ".join(context.args).strip().upper()
        status_msg = await target_message.reply_text(f"⏳ **{query_str}** (미국장) 분석 중...")
        report = analyze_us_stock(query_str)
        await safe_send_or_edit(
            target_message,
            f"🔍 **[미국 종목 실시간 퀀트 분석]**\n\n{report}",
            get_main_menu_keyboard(),
            status_msg=status_msg
        )
        return

    status_msg = await target_message.reply_text("⏳ 미국 증시 데이터를 분석 중입니다...")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_header = f"🗽 **[미국 증시 데일리 분석 리포트]**\n📅 기준시각: `{now_str}`\n"

    macro_data = get_macro_indicators()
    macro_summary = format_macro_summary(macro_data)

    watchlist = get_watchlist("us")
    if watchlist:
        stock_reports = [analyze_us_stock(t) for t in watchlist]
        stocks_section = (
            f"📈 **관심 종목 기술적 & 밸류에이션 분석**\n"
            f"{'-' * 35}\n"
            + "\n\n".join(stock_reports)
        )
    else:
        stocks_section = (
            f"📈 **관심 종목 분석**\n"
            f"{'-' * 35}\n"
            f"• 등록된 미국 관심종목이 없습니다.\n"
            f"• `/add <티커>` (예: `/add AAPL`, `/add TSLA`)로 관심종목을 추가해보세요!"
        )

    full_report = f"{report_header}\n{macro_summary}\n\n{stocks_section}"
    await safe_send_or_edit(target_message, full_report, get_main_menu_keyboard(), status_msg=status_msg)


async def kr_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send KRX market report or analyze specific KR stock if args provided."""
    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if not target_message:
        return

    if context.args:
        query_str = " ".join(context.args).strip()
        kr_code = find_kr_ticker_code(query_str)
        if not kr_code:
            await safe_send_or_edit(
                target_message,
                f"❌ **'{query_str}'** 국내 종목을 찾을 수 없습니다.\n종목명 또는 6자리 코드를 입력해주세요.",
                get_main_menu_keyboard()
            )
            return

        status_msg = await target_message.reply_text(f"⏳ **{query_str}** (국내장) 분석 중...")
        report = analyze_kr_stock(kr_code)
        await safe_send_or_edit(
            target_message,
            f"🔍 **[국내 종목 실시간 퀀트 분석]**\n\n{report}",
            get_main_menu_keyboard(),
            status_msg=status_msg
        )
        return

    status_msg = await target_message.reply_text("⏳ 국내 증시(KRX) 데이터를 분석 중입니다...")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_header = f"🏯 **[국내 증시(KRX) 데일리 분석 리포트]**\n📅 기준시각: `{now_str}`\n"

    usd_fx = get_single_macro_indicator("KRW=X", "원/달러 환율 (USD/KRW)", "원", multiplier=1.0)
    jpy_fx = get_single_macro_indicator("JPYKRW=X", "엔/원 환율 (100JPY/KRW)", "원", multiplier=100.0)

    fx_lines = ["💱 **주요 환율 및 거시경제 상황**", "-" * 35]
    if usd_fx.get("status") == "OK" and usd_fx.get("price") is not None:
        u_pct = usd_fx.get("change_pct", 0.0)
        u_sign = "🔺 " if u_pct > 0 else ("🔻 " if u_pct < 0 else "➖ ")
        fx_lines.append(f"• **원/달러 (USD/KRW)**: `{usd_fx['price']:,.2f}원` ({u_sign}{u_pct:+.2f}%)")
    else:
        fx_lines.append(f"• **원/달러 환율**: `조회 실패`")

    if jpy_fx.get("status") == "OK" and jpy_fx.get("price") is not None:
        j_pct = jpy_fx.get("change_pct", 0.0)
        j_sign = "🔺 " if j_pct > 0 else ("🔻 " if j_pct < 0 else "➖ ")
        fx_lines.append(f"• **엔/원 (100엔당)**: `{jpy_fx['price']:,.2f}원` ({j_sign}{j_pct:+.2f}%)")
    else:
        fx_lines.append(f"• **엔/원 환율**: `조회 실패`")

    fx_summary = "\n".join(fx_lines)

    watchlist = get_watchlist("kr")
    if watchlist:
        stock_reports = [analyze_kr_stock(t) for t in watchlist]
        stocks_section = (
            f"📊 **국내 주요 종목 분석**\n"
            f"{'-' * 35}\n"
            + "\n\n".join(stock_reports)
        )
    else:
        stocks_section = (
            f"📊 **국내 종목 분석**\n"
            f"{'-' * 35}\n"
            f"• 등록된 국내 관심종목이 없습니다.\n"
            f"• `/add <종목명>` (예: `/add 삼성전자`, `/add 카카오`)로 관심종목을 추가해보세요!"
        )

    full_report = f"{report_header}\n{fx_summary}\n\n{stocks_section}"
    await safe_send_or_edit(target_message, full_report, get_main_menu_keyboard(), status_msg=status_msg)


async def macro_report_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Generate and send macro indicators summary."""
    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if target_message:
        status_msg = await target_message.reply_text("⏳ 글로벌 매크로 지표를 수집 중입니다...")
        macro_data = get_macro_indicators()
        macro_summary = format_macro_summary(macro_data)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        report = f"🌐 **[글로벌 매크로 & 원자재 지표]**\n📅 기준시각: `{now_str}`\n\n{macro_summary}"
        await safe_send_or_edit(target_message, report, get_main_menu_keyboard(), status_msg=status_msg)


async def screener_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run multi-strategy quant screener and send report."""
    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if target_message:
        status_msg = await target_message.reply_text("⏳ 퀀트 스크리너가 국내/미국 대표 종목을 분석 중입니다 (약 3~5초 소요)...")
        screen_data = run_quant_screener()
        report = format_screener_report(screen_data)
        await safe_send_or_edit(target_message, report, get_main_menu_keyboard(), status_msg=status_msg)


async def calendar_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send economic calendar and earnings D-Day report."""
    target_message = update.message or (update.callback_query.message if update.callback_query else None)
    if target_message:
        status_msg = await target_message.reply_text("⏳ 글로벌 경제 일정 및 실적 일정을 조회 중입니다...")
        report = format_economic_calendar_report()
        await safe_send_or_edit(target_message, report, get_main_menu_keyboard(), status_msg=status_msg)


async def button_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button clicks."""
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "btn_us":
        await us_report_handler(update, context)
    elif data == "btn_kr":
        await kr_report_handler(update, context)
    elif data == "btn_screener":
        await screener_command_handler(update, context)
    elif data == "btn_calendar":
        await calendar_command_handler(update, context)
    elif data == "btn_macro":
        await macro_report_handler(update, context)
    elif data == "btn_watchlist":
        await watchlist_command_handler(update, context)
    elif data == "btn_help":
        help_text = (
            "💡 **[종목 조회 및 관리 팁]**\n\n"
            "1️⃣ **종목 바로 분석 (AI 퀀트 진단 포함)**\n"
            "채팅창에 원하는 종목을 바로 입력해보세요:\n"
            "• **국내장**: `삼성전자`, `005930`, `리노공업`, `카카오`, `SK하이닉스`\n"
            "• **미국장**: `TSLA`, `AAPL`, `NVDA`, `MSFT`, `ON`, `OPEN`\n\n"
            "2️⃣ **핵심 기능 바로가기**\n"
            "• `🎯 퀀트 유망주 발굴` : 20일선 돌파 & 낙폭과대 반등 유망주 Top 5\n"
            "• `📅 경제 일정 & 실적 D-Day` : FOMC, CPI 및 관심종목 어닝 디데이\n\n"
            "3️⃣ **관심종목 추가/삭제**\n"
            "• 추가: `/add MSFT` 또는 `/add 카카오`\n"
            "• 삭제: `/del TSLA` 또는 `/del 삼성전자`\n"
            "• 목록: `/list`"
        )
        if query.message:
            await safe_send_or_edit(query.message, help_text, get_main_menu_keyboard())


def process_stock_query(query_text: str) -> str:
    """
    Intelligently route and analyze stock query using Smart Classifier.
    """
    clean_text = query_text.strip()
    if not clean_text:
        return "⚠️ 검색할 종목명이나 티커를 입력해주세요."

    market, target = route_stock_query(clean_text)

    # 1. US Stock First Route (Alphabet-only query or explicit /us)
    if market == "US":
        report = analyze_us_stock(target)
        if "데이터 수집 불가" not in report:
            return f"🔍 **[미국 종목 실시간 퀀트 분석]**\n\n{report}"
        # Secondary fallback: Check if user typed English name for KR stock (e.g., 'posco')
        kr_code = find_kr_ticker_code(clean_text)
        if kr_code:
            kr_report = analyze_kr_stock(kr_code)
            return f"🔍 **[국내 종목 실시간 퀀트 분석]**\n\n{kr_report}"

    # 2. KRX Stock Route (Contains Hangul, 6-digits, or explicit /kr)
    elif market == "KR":
        kr_code = find_kr_ticker_code(target)
        if kr_code:
            report = analyze_kr_stock(kr_code)
            return f"🔍 **[국내 종목 실시간 퀀트 분석]**\n\n{report}"
        # Secondary fallback: Check US
        us_report = analyze_us_stock(clean_text.upper())
        if "데이터 수집 불가" not in us_report:
            return f"🔍 **[미국 종목 실시간 퀀트 분석]**\n\n{us_report}"

    # 3. Fallback: Not found
    return (
        f"❌ **'{clean_text}' 종목을 찾을 수 없습니다.**\n\n"
        f"• **미국 티커 예시**: `AAPL`, `TSLA`, `ON`, `AI`, `OPEN`\n"
        f"• **국내 종목 예시**: `삼성전자`, `리노공업`, `SB성보`, `005930`\n"
        f"• **명시적 검색**: `/us ON` 또는 `/kr 성보`"
    )


async def check_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /check <query> command."""
    if not context.args:
        if update.message:
            await safe_send_or_edit(
                update.message,
                "⚠️ 조회할 종목을 입력해주세요.\n예시: `/check TSLA` 또는 `/check 삼성전자`",
                get_main_menu_keyboard()
            )
        return

    query_str = " ".join(context.args)
    if update.message:
        status_msg = await update.message.reply_text(f"⏳ **{query_str}** 종목을 분석 중입니다...")
        result_text = process_stock_query(query_str)
        await safe_send_or_edit(update.message, result_text, get_main_menu_keyboard(), status_msg=status_msg)


async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle arbitrary text inputs as stock queries."""
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    if text.startswith("/"):
        return  # Handled by command handlers

    status_msg = await update.message.reply_text(f"⏳ **{text}** 분석 중...")
    result_text = process_stock_query(text)
    await safe_send_or_edit(update.message, result_text, get_main_menu_keyboard(), status_msg=status_msg)


def run_interactive_bot() -> None:
    """Start polling loop for interactive telegram bot."""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token or "your_telegram" in token.lower():
        print("❌ Error: TELEGRAM_BOT_TOKEN is not configured in .env file.")
        return

    print("🚀 Interactive Telegram Stock Bot is starting polling...")
    print("Press Ctrl+C to stop.")

    app = ApplicationBuilder().token(token).build()

    # Register Command Handlers
    app.add_handler(CommandHandler(["start", "menu"], start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler(["us", "usa"], us_report_handler))
    app.add_handler(CommandHandler(["kr", "kor", "krx"], kr_report_handler))
    app.add_handler(CommandHandler("macro", macro_report_handler))
    app.add_handler(CommandHandler(["screen", "screener", "pick"], screener_command_handler))
    app.add_handler(CommandHandler(["calendar", "events", "dday"], calendar_command_handler))
    app.add_handler(CommandHandler(["list", "watchlist"], watchlist_command_handler))
    app.add_handler(CommandHandler("add", add_command_handler))
    app.add_handler(CommandHandler(["del", "remove"], del_command_handler))
    app.add_handler(CommandHandler(["check", "stock"], check_command_handler))

    # Register Callback Query Handler for Buttons
    app.add_handler(CallbackQueryHandler(button_callback_handler))

    # Register General Text Message Handler (auto stock detection)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))

    # Run polling loop
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    run_interactive_bot()
