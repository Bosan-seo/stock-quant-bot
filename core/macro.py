"""
Macro indicators module using yfinance.
Fetches VIX, US 10Y Treasury Yield, Dollar Index, WTI Crude Oil, USD/KRW, and JPY/KRW (100JPY) Exchange Rates.
"""
import yfinance as yf
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

MACRO_TICKERS = {
    "^VIX": {"name": "VIX 변동성 지수", "unit": "pt", "multiplier": 1.0},
    "^TNX": {"name": "미국채 10년물 금리", "unit": "%", "multiplier": 1.0},
    "DX-Y.NYB": {"name": "달러 인덱스 (DXY)", "unit": "pt", "multiplier": 1.0},
    "CL=F": {"name": "WTI 유가", "unit": "$", "multiplier": 1.0},
    "KRW=X": {"name": "원/달러 환율 (USD/KRW)", "unit": "원", "multiplier": 1.0},
    "JPYKRW=X": {"name": "엔/원 환율 (100엔)", "unit": "원", "multiplier": 100.0},
}


def get_single_macro_indicator(ticker: str, name: str, unit: str, multiplier: float = 1.0) -> Dict[str, Any]:
    """
    Fetch the latest price and daily change for a single macro ticker.
    """
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d")
        if hist.empty or len(hist) < 1:
            return {
                "ticker": ticker,
                "name": name,
                "unit": unit,
                "price": None,
                "prev_price": None,
                "change": None,
                "change_pct": None,
                "status": "No data",
            }

        hist = hist.dropna(subset=['Close'])
        latest_price = float(hist['Close'].iloc[-1]) * multiplier
        if len(hist) >= 2:
            prev_price = float(hist['Close'].iloc[-2]) * multiplier
            change = latest_price - prev_price
            change_pct = (change / prev_price) * 100
        else:
            prev_price = latest_price
            change = 0.0
            change_pct = 0.0

        return {
            "ticker": ticker,
            "name": name,
            "unit": unit,
            "price": round(latest_price, 2),
            "prev_price": round(prev_price, 2),
            "change": round(change, 2),
            "change_pct": round(change_pct, 2),
            "status": "OK",
        }
    except Exception as e:
        logger.warning(f"Failed to fetch macro data for {ticker}: {e}")
        return {
            "ticker": ticker,
            "name": name,
            "unit": unit,
            "price": None,
            "prev_price": None,
            "change": None,
            "change_pct": None,
            "status": f"Error: {str(e)}",
        }


def get_macro_indicators(tickers_map: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, Dict[str, Any]]:
    """
    Fetch all major macroeconomic indicators.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of ticker -> indicator details.
    """
    if tickers_map is None:
        tickers_map = MACRO_TICKERS

    results = {}
    for ticker, info in tickers_map.items():
        multiplier = float(info.get("multiplier", 1.0))
        results[ticker] = get_single_macro_indicator(ticker, info["name"], info["unit"], multiplier=multiplier)
    return results


def format_macro_summary(macro_data: Dict[str, Dict[str, Any]]) -> str:
    """
    Format macro indicators into a Markdown string for reports.
    """
    lines = ["📊 **글로벌 매크로 및 주요 환율 브리핑**"]
    lines.append("-" * 35)

    for ticker, data in macro_data.items():
        name = data.get("name", ticker)
        unit = data.get("unit", "")
        status = data.get("status", "")
        
        if status == "OK" and data.get("price") is not None:
            price = data["price"]
            change_pct = data.get("change_pct", 0.0)
            sign = "🔺 " if change_pct > 0 else ("🔻 " if change_pct < 0 else "➖ ")
            lines.append(f"• **{name}**: `{price:,.2f}{unit}` ({sign}{change_pct:+.2f}%)")
        else:
            lines.append(f"• **{name}**: `데이터 수집 실패 ({status})`")

    return "\n".join(lines)
