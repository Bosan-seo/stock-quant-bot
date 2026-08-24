"""
US Stock Analysis Bot Main Pipeline.
Fetches macro data, calculates technical indicators and valuations for US stocks,
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

from core.macro import get_macro_indicators, format_macro_summary
from core.indicators import add_technical_indicators
from core.notifier import send_telegram_message
from core.ai_analyzer import generate_quant_opinion
from us_bot.fetcher import get_us_stock_data


from core.watchlist import get_watchlist

DEFAULT_WATCHLIST = []


def analyze_us_stock(ticker: str) -> str:
    """
    Fetch stock data, compute technical indicators, and generate analysis summary.
    """
    df, valuation = get_us_stock_data(ticker, period="6mo")
    if df is None or df.empty or len(df) < 20:
        return f"### 🇺🇸 {ticker}\n- ⚠️ 데이터 수집 불가 또는 데이터 수 부족\n"

    # Add indicators
    df = add_technical_indicators(df, price_col='Close')

    latest = df.iloc[-1]
    prev = df.iloc[-2]

    close_price = float(latest['Close'])
    prev_close = float(prev['Close'])
    change_val = close_price - prev_close
    change_pct = ((close_price - prev_close) / prev_close) * 100

    sma20 = float(latest['SMA20']) if not pd.isna(latest['SMA20']) else None
    prev_sma20 = float(prev['SMA20']) if not pd.isna(prev['SMA20']) else None
    rsi14 = float(latest['RSI14']) if not pd.isna(latest['RSI14']) else None
    macd = float(latest['MACD']) if not pd.isna(latest['MACD']) else None
    macd_signal = float(latest['MACD_Signal']) if not pd.isna(latest['MACD_Signal']) else None

    # Price Line
    if change_val > 0:
        price_line = f"`${close_price:,.2f}` (🔺 +${change_val:,.2f} / `+{change_pct:.2f}%`)"
    elif change_val < 0:
        price_line = f"`${close_price:,.2f}` (🔻 -${abs(change_val):,.2f} / `{change_pct:.2f}%`)"
    else:
        price_line = f"`${close_price:,.2f}` (➖ 보합 `0.00%`)"

    # SMA 20 Status
    sma_status = "정보 없음"
    if sma20 is not None:
        if prev_sma20 and prev_close < prev_sma20 and close_price >= sma20:
            sma_status = f"🚀 **20일선 상향 돌파** (${sma20:,.2f})"
        elif prev_sma20 and prev_close > prev_sma20 and close_price <= sma20:
            sma_status = f"⚠️ **20일선 하향 이탈** (${sma20:,.2f})"
        elif close_price >= sma20:
            sma_status = f"🟢 **20일선 상회** (${sma20:,.2f})"
        else:
            sma_status = f"🔴 **20일선 하회** (${sma20:,.2f})"

    # RSI Status
    rsi_status = "정보 없음"
    if rsi14 is not None:
        if rsi14 >= 70:
            rsi_status = f"🔥 **과매수 경계** (`{rsi14:.1f}`)"
        elif rsi14 <= 30:
            rsi_status = f"🧊 **과매도 반등 기대** (`{rsi14:.1f}`)"
        else:
            rsi_status = f"⚖️ **중립** (`{rsi14:.1f}`)"

    # MACD Status
    macd_status = "정보 없음"
    if macd is not None and macd_signal is not None:
        if macd >= macd_signal:
            macd_status = "📈 **골든크로스 / 상승 추세 유지**"
        else:
            macd_status = "📉 **데드크로스 / 하락 조정 추세**"

    # Valuations
    name = valuation.get("name", ticker)
    pe = f"{valuation['pe']:.2f}배" if valuation.get("pe") is not None else "N/A"
    pbr = f"{valuation['pbr']:.2f}배" if valuation.get("pbr") is not None else "N/A"
    roe = f"{valuation['roe']:.2f}%" if valuation.get("roe") is not None else "N/A"

    # AI Quant Opinion
    quant_payload = {
        "market": "US",
        "name": name,
        "ticker": ticker,
        "price": close_price,
        "prev_close": prev_close,
        "change_pct": change_pct,
        "sma20": sma20,
        "prev_sma20": prev_sma20,
        "rsi14": rsi14,
        "macd": macd,
        "macd_signal": macd_signal,
        "per": valuation.get("pe"),
        "pbr": valuation.get("pbr"),
        "div_yield": None,
        "roe": valuation.get("roe"),
    }
    ai_opinion = generate_quant_opinion(quant_payload)

    lines = [
        f"### 🇺🇸 **{name} ({ticker})**",
        f"- **현재가**: {price_line}",
        f"- **20일 이평선**: {sma_status}",
        f"- **RSI (14)**: {rsi_status}",
        f"- **MACD (12,26,9)**: {macd_status}",
        f"- **밸류에이션**: `PER: {pe}` | `PBR: {pbr}` | `ROE: {roe}`",
        f"\n{ai_opinion}",
    ]
    return "\n".join(lines)


def run_us_bot(watchlist=None) -> str:
    """
    Run US stock analysis workflow.
    """
    if watchlist is None:
        watchlist = get_watchlist("us")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report_header = f"🗽 **[미국 증시 데일리 분석 리포트]**\n📅 기준시각: `{now_str}`"

    # 1. Market Indices & News
    from core.market_indices import get_us_market_indices, format_indices_summary
    from core.news_fetcher import get_us_market_news, format_news_summary
    from core.ai_analyzer import generate_market_opinion

    indices_data = get_us_market_indices()
    indices_summary = format_indices_summary(indices_data, title="미국 3대 시장 지수 현황")

    news_items = get_us_market_news(limit=3)
    news_summary = format_news_summary(news_items, title="오늘의 미국 증시 핵심 뉴스")

    market_ai_opinion = generate_market_opinion("US", indices_data, news_items)

    # 2. US Stocks Technical & Valuation Analysis
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

    full_report = f"{report_header}\n\n{indices_summary}\n\n{news_summary}\n\n{market_ai_opinion}\n\n{stocks_section}"

    # 3. Send Notification
    send_telegram_message(full_report)
    return full_report


if __name__ == "__main__":
    import pandas as pd
    print("Starting US Stock Bot pipeline...")
    run_us_bot()
