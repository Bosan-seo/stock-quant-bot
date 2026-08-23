"""
Korean Stock Analysis Bot Main Pipeline.
Fetches USD/KRW macro status, calculates technical indicators and valuations for KRX stocks,
and dispatches an executive summary report via Telegram.
"""
import os
import sys
from datetime import datetime
import pandas as pd

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.macro import get_single_macro_indicator
from core.indicators import add_technical_indicators
from core.notifier import send_telegram_message
from core.ai_analyzer import generate_quant_opinion
from kr_bot.fetcher import get_kr_stock_data
from core.watchlist import get_watchlist

DEFAULT_KR_WATCHLIST = []


def analyze_kr_stock(ticker_code: str) -> str:
    """
    Fetch KRX stock data, compute technical indicators, and generate analysis summary.
    """
    df, valuation = get_kr_stock_data(ticker_code, days=180)
    name = valuation.get("name", ticker_code)

    if df is None or df.empty or len(df) < 20:
        return f"### 🇰🇷 **{name} ({ticker_code})**\n- ⚠️ 데이터 수집 불가 또는 거래 데이터 부족\n"

    # Add indicators
    df = add_technical_indicators(df, price_col='Close')

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    # Use official realtime quote if available, fallback to daily bar
    if valuation.get("current_price") is not None:
        close_price = float(valuation["current_price"])
        change_val = float(valuation.get("change_price", 0.0))
        change_type = valuation.get("change_type", "SAME")
        change_pct = float(valuation.get("change_rate", 0.0))
        if change_type == "FALLING" and change_val > 0:
            change_val = -change_val
        if change_type == "FALLING" and change_pct > 0:
            change_pct = -change_pct
        prev_close = float(valuation.get("prev_close") or (close_price - change_val))
    else:
        close_price = float(latest['Close'])
        prev_close = float(prev['Close'])
        change_val = close_price - prev_close
        change_pct = ((close_price - prev_close) / prev_close) * 100

    sma20 = float(latest['SMA20']) if not pd.isna(latest['SMA20']) else None
    prev_sma20 = float(prev['SMA20']) if not pd.isna(prev['SMA20']) else None
    rsi14 = float(latest['RSI14']) if not pd.isna(latest['RSI14']) else None
    macd = float(latest['MACD']) if not pd.isna(latest['MACD']) else None
    macd_signal = float(latest['MACD_Signal']) if not pd.isna(latest['MACD_Signal']) else None

    # 1. Price Change Formatting
    if change_val > 0 or change_pct > 0:
        price_line = f"`{close_price:,.0f}원` (🔺 +{abs(change_val):,.0f}원 / `+{abs(change_pct):.2f}%`)"
    elif change_val < 0 or change_pct < 0:
        price_line = f"`{close_price:,.0f}원` (🔻 -{abs(change_val):,.0f}원 / `-{abs(change_pct):.2f}%`)"
    else:
        price_line = f"`{close_price:,.0f}원` (➖ 보합 `0.00%`)"

    # 2. SMA 20 Status
    sma_status = "정보 없음"
    if sma20 is not None:
        if prev_sma20 and prev_close < prev_sma20 and close_price >= sma20:
            sma_status = f"🚀 **20일선 상향 돌파** ({sma20:,.0f}원)"
        elif prev_sma20 and prev_close > prev_sma20 and close_price <= sma20:
            sma_status = f"⚠️ **20일선 하향 이탈** ({sma20:,.0f}원)"
        elif close_price >= sma20:
            sma_status = f"🟢 **20일선 상회** ({sma20:,.0f}원)"
        else:
            sma_status = f"🔴 **20일선 하회** ({sma20:,.0f}원)"

    # 3. RSI Status
    rsi_status = "정보 없음"
    if rsi14 is not None:
        if rsi14 >= 70:
            rsi_status = f"🔥 **과매수 경계** (`{rsi14:.1f}`)"
        elif rsi14 <= 30:
            rsi_status = f"🧊 **과매도 반등 기대** (`{rsi14:.1f}`)"
        else:
            rsi_status = f"⚖️ **중립** (`{rsi14:.1f}`)"

    # 4. MACD Status
    macd_status = "정보 없음"
    if macd is not None and macd_signal is not None:
        if macd >= macd_signal:
            macd_status = "📈 **골든크로스 / 상승 추세 유지**"
        else:
            macd_status = "📉 **데드크로스 / 하락 조정 추세**"

    # 5. Valuations & Financials
    per = f"{valuation['per']:.2f}배" if valuation.get("per") is not None else "N/A"
    pbr = f"{valuation['pbr']:.2f}배" if valuation.get("pbr") is not None else "N/A"
    div_yield = f"{valuation['div']:.2f}%" if valuation.get("div") is not None else "N/A"
    eps = f"{valuation['eps']:,.0f}원" if valuation.get("eps") is not None else "N/A"
    bps = f"{valuation['bps']:,.0f}원" if valuation.get("bps") is not None else "N/A"

    market_cap = valuation.get("market_cap", "N/A")
    week52_high = valuation.get("week52_high", "N/A")
    week52_low = valuation.get("week52_low", "N/A")

    lines = [
        f"### 🇰🇷 **{name} ({ticker_code})**",
        f"- **현재가**: {price_line}",
    ]

    # Add range & market cap if available
    if market_cap != "N/A" or week52_high != "N/A":
        lines.append(f"- **기업규모/범위**: `시총: {market_cap}` | `52주: {week52_low} ~ {week52_high}`")

    # 6. AI Quant Diagnosis
    quant_payload = {
        "market": "KR",
        "name": name,
        "ticker": ticker_code,
        "price": close_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "sma20": sma20,
        "prev_sma20": prev_sma20,
        "rsi14": rsi14,
        "macd": macd,
        "macd_signal": macd_signal,
        "per": valuation.get("per"),
        "pbr": valuation.get("pbr"),
        "div_yield": valuation.get("div"),
        "roe": None,
    }
    ai_opinion = generate_quant_opinion(quant_payload)

    lines.extend([
        f"- **20일 이평선**: {sma_status}",
        f"- **RSI (14)**: {rsi_status}",
        f"- **MACD (12,26,9)**: {macd_status}",
        f"- **밸류에이션**: `PER: {per}` | `PBR: {pbr}` | `배당수익률: {div_yield}`",
        f"- **주당 가치**: `EPS: {eps}` | `BPS: {bps}`",
        f"\n{ai_opinion}",
    ])

    return "\n".join(lines)


def run_kr_bot(watchlist=None) -> str:
    """
    Run Korean stock analysis workflow.
    """
    if watchlist is None:
        watchlist = get_watchlist("kr")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_header = f"🏯 **[국내 증시(KRX) 데일리 분석 리포트]**\n📅 기준시각: `{now_str}`\n"

    # 1. Macro: USD/KRW & JPY/KRW Exchange rate
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

    # 2. KRX Stocks Technical & Valuation Analysis
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

    # 3. Send Notification
    send_telegram_message(full_report)
    return full_report


if __name__ == "__main__":
    print("Starting KR Stock Bot pipeline...")
    run_kr_bot()
