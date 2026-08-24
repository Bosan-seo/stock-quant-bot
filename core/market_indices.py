"""
Market Indices Module.
Fetches real-time market indices for US (S&P 500, NASDAQ, Dow Jones, Russell 2000)
and KRX (KOSPI, KOSDAQ).
"""
import yfinance as yf
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

US_INDICES_CONFIG = [
    {"ticker": "^GSPC", "name": "S&P 500", "icon": "🇺🇸"},
    {"ticker": "^IXIC", "name": "나스닥 (NASDAQ)", "icon": "💻"},
    {"ticker": "^DJI", "name": "다우 존스 (Dow)", "icon": "🏛️"},
    {"ticker": "^RUT", "name": "러셀 2000 (Small-Cap)", "icon": "🏢"},
]

KR_INDICES_CONFIG = [
    {"ticker": "^KS11", "name": "코스피 (KOSPI)", "icon": "🏯"},
    {"ticker": "^KQ11", "name": "코스닥 (KOSDAQ)", "icon": "🚀"},
]


def _fetch_single_index(ticker: str, name: str, icon: str) -> Dict[str, Any]:
    """Fetch single index price and daily change."""
    try:
        t = yf.Ticker(ticker)
        info = t.fast_info
        last_price = info.last_price
        prev_close = info.previous_close

        if last_price is not None and prev_close is not None and prev_close > 0:
            change = last_price - prev_close
            change_pct = (change / prev_close) * 100
            return {
                "ticker": ticker,
                "name": name,
                "icon": icon,
                "price": last_price,
                "change": change,
                "change_pct": change_pct,
                "status": "OK"
            }
    except Exception as e:
        logger.debug(f"Failed to fetch index {ticker}: {e}")

    return {
        "ticker": ticker,
        "name": name,
        "icon": icon,
        "price": None,
        "change": None,
        "change_pct": None,
        "status": "FAILED"
    }


def get_us_market_indices() -> List[Dict[str, Any]]:
    """Fetch US major market indices."""
    results = []
    for item in US_INDICES_CONFIG:
        results.append(_fetch_single_index(item["ticker"], item["name"], item["icon"]))
    return results


def get_kr_market_indices() -> List[Dict[str, Any]]:
    """Fetch Korean major market indices."""
    results = []
    for item in KR_INDICES_CONFIG:
        results.append(_fetch_single_index(item["ticker"], item["name"], item["icon"]))
    return results


def format_indices_summary(indices: List[Dict[str, Any]], title: str = "주요 시장 지수 현황") -> str:
    """Format market indices list into clean telegram markdown summary."""
    lines = [f"📊 **{title}**", "-" * 35]
    for idx in indices:
        icon = idx.get("icon", "📈")
        name = idx.get("name", "지수")
        if idx.get("status") == "OK" and idx.get("price") is not None:
            price = idx["price"]
            change = idx["change"]
            change_pct = idx["change_pct"]
            
            if change > 0:
                sign_icon = "🔺"
                sign_str = "+"
            elif change < 0:
                sign_icon = "🔻"
                sign_str = ""
            else:
                sign_icon = "➖"
                sign_str = ""

            lines.append(
                f"• {icon} **{name}**: `{price:,.2f}` ({sign_icon} `{sign_str}{change:,.2f}` / `{change_pct:+.2f}%`)"
            )
        else:
            lines.append(f"• {icon} **{name}**: `조회 지연`")

    return "\n".join(lines)
