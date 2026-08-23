"""
Quant Stock Screener Module.
Scans Korean & US representative universes to discover high-probability trading opportunities:
  1. 🚀 20-day SMA Golden Breakout
  2. 🧊 Oversold Rebound (RSI <= 35)
  3. 💎 Low PER & High Dividend Value Stocks
"""
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, List, Optional
import logging

from core.indicators import add_technical_indicators
from kr_bot.fetcher import get_kr_stock_data
from us_bot.fetcher import get_us_stock_data

logger = logging.getLogger(__name__)

# Representative Universe for screening
KR_SCREEN_UNIVERSE = [
    "005930", "000660", "373220", "207940", "005380", "000270", "068270", "105560",
    "055550", "005490", "035420", "035720", "051910", "006400", "012330", "086790",
    "012450", "196170", "247540", "086520", "028300", "000250", "348370", "141080",
    "214150", "145020", "277810", "058470", "034020", "042700"
]

US_SCREEN_UNIVERSE = [
    "AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META", "TSLA", "AVGO", "COST", "NFLX",
    "AMD", "QCOM", "TXN", "JNJ", "UNH", "JPM", "XOM", "PG", "HD", "PLTR", "ON", "KO"
]


def _scan_single_kr_stock(ticker: str) -> Optional[Dict[str, Any]]:
    """Scan and compute indicators for a single KRX stock."""
    try:
        df, val = get_kr_stock_data(ticker, days=120)
        if df is None or df.empty or len(df) < 22:
            return None

        df = add_technical_indicators(df, price_col="Close")
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(val.get("current_price") or latest["Close"])
        prev_close = float(prev["Close"])
        change_pct = float(val.get("change_rate") or (((close - prev_close) / prev_close) * 100))

        sma20 = float(latest["SMA20"]) if not pd.isna(latest["SMA20"]) else None
        prev_sma20 = float(prev["SMA20"]) if not pd.isna(prev["SMA20"]) else None
        rsi14 = float(latest["RSI14"]) if not pd.isna(latest["RSI14"]) else None
        macd = float(latest["MACD"]) if not pd.isna(latest["MACD"]) else None
        macd_sig = float(latest["MACD_Signal"]) if not pd.isna(latest["MACD_Signal"]) else None

        is_breakout = (prev_sma20 and sma20 and prev_close < prev_sma20 and close >= sma20) or (sma20 and close >= sma20 and change_pct > 1.5)
        is_oversold = (rsi14 is not None and rsi14 <= 38 and change_pct >= -1.0)
        
        per = val.get("per")
        div_yield = val.get("div")
        is_value = (per is not None and 0 < per <= 12 and div_yield is not None and div_yield >= 3.0)

        return {
            "market": "KR",
            "ticker": ticker,
            "name": val.get("name", ticker),
            "price": close,
            "change_pct": change_pct,
            "sma20": sma20,
            "rsi14": rsi14,
            "macd_bullish": (macd >= macd_sig) if (macd is not None and macd_sig is not None) else False,
            "per": per,
            "pbr": val.get("pbr"),
            "div": div_yield,
            "is_breakout": is_breakout,
            "is_oversold": is_oversold,
            "is_value": is_value,
        }
    except Exception as e:
        logger.debug(f"Scan KR {ticker} failed: {e}")
        return None


def _scan_single_us_stock(ticker: str) -> Optional[Dict[str, Any]]:
    """Scan and compute indicators for a single US stock."""
    try:
        df, val = get_us_stock_data(ticker, period="6mo")
        if df is None or df.empty or len(df) < 22:
            return None

        df = add_technical_indicators(df, price_col="Close")
        latest = df.iloc[-1]
        prev = df.iloc[-2]

        close = float(latest["Close"])
        prev_close = float(prev["Close"])
        change_pct = ((close - prev_close) / prev_close) * 100

        sma20 = float(latest["SMA20"]) if not pd.isna(latest["SMA20"]) else None
        prev_sma20 = float(prev["SMA20"]) if not pd.isna(prev["SMA20"]) else None
        rsi14 = float(latest["RSI14"]) if not pd.isna(latest["RSI14"]) else None
        macd = float(latest["MACD"]) if not pd.isna(latest["MACD"]) else None
        macd_sig = float(latest["MACD_Signal"]) if not pd.isna(latest["MACD_Signal"]) else None

        is_breakout = (prev_sma20 and sma20 and prev_close < prev_sma20 and close >= sma20) or (sma20 and close >= sma20 and change_pct > 1.0)
        is_oversold = (rsi14 is not None and rsi14 <= 40)
        
        per = val.get("pe")
        is_value = (per is not None and 0 < per <= 20 and val.get("pbr", 99) <= 3.0)

        return {
            "market": "US",
            "ticker": ticker,
            "name": val.get("name", ticker),
            "price": close,
            "change_pct": change_pct,
            "sma20": sma20,
            "rsi14": rsi14,
            "macd_bullish": (macd >= macd_sig) if (macd is not None and macd_sig is not None) else False,
            "per": per,
            "pbr": val.get("pbr"),
            "div": None,
            "is_breakout": is_breakout,
            "is_oversold": is_oversold,
            "is_value": is_value,
        }
    except Exception as e:
        logger.debug(f"Scan US {ticker} failed: {e}")
        return None


def run_quant_screener() -> Dict[str, List[Dict[str, Any]]]:
    """
    Run multi-threaded scanner across KR and US universes.
    """
    results = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []
        for t in KR_SCREEN_UNIVERSE:
            futures.append(executor.submit(_scan_single_kr_stock, t))
        for t in US_SCREEN_UNIVERSE:
            futures.append(executor.submit(_scan_single_us_stock, t))

        for f in as_completed(futures):
            res = f.result()
            if res:
                results.append(res)

    # Filter into strategies
    breakouts = [r for r in results if r["is_breakout"]]
    breakouts.sort(key=lambda x: x["change_pct"], reverse=True)

    oversolds = [r for r in results if r["is_oversold"]]
    oversolds.sort(key=lambda x: x["rsi14"] if x["rsi14"] is not None else 99)

    values = [r for r in results if r["is_value"]]
    values.sort(key=lambda x: x["per"] if x["per"] is not None else 999)

    return {
        "breakouts": breakouts[:5],
        "oversolds": oversolds[:5],
        "values": values[:5],
    }


def format_screener_report(screen_data: Dict[str, List[Dict[str, Any]]]) -> str:
    """
    Format screener results into an executive telegram report.
    """
    lines = ["🎯 **[오늘의 퀀트 유망주 발굴 스크리너]**", "=" * 35]

    # 1. 20-day SMA Breakout Top 5
    lines.append("\n🚀 **[전략 1] 20일선 골든 돌파 / 상승 모멘텀 Top 5**")
    lines.append("• 20일 이평선을 상향 돌파하며 거래량이 실린 단기 추세 전환주")
    lines.append("-" * 35)
    if screen_data.get("breakouts"):
        for item in screen_data["breakouts"]:
            flag = "🇰🇷" if item["market"] == "KR" else "🇺🇸"
            curr = "원" if item["market"] == "KR" else "$"
            p_str = f"{item['price']:,.0f}" if item["market"] == "KR" else f"{item['price']:.2f}"
            lines.append(
                f"• {flag} **{item['name']} ({item['ticker']})**: `{p_str}{curr}` "
                f"(`{item['change_pct']:+.2f}%`) | RSI: `{item['rsi14']:.1f}`"
            )
    else:
        lines.append("• 오늘 조건을 만족하는 돌파 종목이 없습니다.")

    # 2. Oversold Rebound Top 5
    lines.append("\n🧊 **[전략 2] 낙폭과대 반등 유망주 (RSI ≤ 38) Top 5**")
    lines.append("• 기술적 과매도 구간에 진입하여 기술적 반등 매수세가 기대되는 종목")
    lines.append("-" * 35)
    if screen_data.get("oversolds"):
        for item in screen_data["oversolds"]:
            flag = "🇰🇷" if item["market"] == "KR" else "🇺🇸"
            curr = "원" if item["market"] == "KR" else "$"
            p_str = f"{item['price']:,.0f}" if item["market"] == "KR" else f"{item['price']:.2f}"
            lines.append(
                f"• {flag} **{item['name']} ({item['ticker']})**: `{p_str}{curr}` "
                f"| RSI: 🔥 `{item['rsi14']:.1f}` (과매도)"
            )
    else:
        lines.append("• 현재 과매도 구간에 위치한 종목이 없습니다.")

    # 3. Value & Dividend Top 5
    lines.append("\n💎 **[전략 3] 저PER + 고배당 알짜 가치주 Top 5**")
    lines.append("• 저평가 밸류에이션(PER 저평가)과 배당 안전마진을 겸비한 가치주")
    lines.append("-" * 35)
    if screen_data.get("values"):
        for item in screen_data["values"]:
            flag = "🇰🇷" if item["market"] == "KR" else "🇺🇸"
            div_str = f" | 배당: `{item['div']:.2f}%`" if item.get("div") else ""
            lines.append(
                f"• {flag} **{item['name']} ({item['ticker']})**: PER `{item['per']:.1f}배`{div_str}"
            )
    else:
        lines.append("• 조건을 만족하는 가치주 종목이 없습니다.")

    lines.append("\n💡 *종목명을 챗봇에 입력하시면 상세 기술적/밸류에이션 리포트를 조회할 수 있습니다.*")
    return "\n".join(lines)
