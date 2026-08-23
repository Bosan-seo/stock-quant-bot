"""
Watchlist management module.
Persists US and KR stock watchlists in a JSON file and provides add/remove/list operations.
"""
import os
import json
import logging
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)

WATCHLIST_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "watchlist.json"
)

DEFAULT_WATCHLIST_DATA = {
    "us": [],
    "kr": []
}


def load_watchlist() -> Dict[str, List[str]]:
    """Load watchlist from JSON file, creating default if not exists."""
    if not os.path.exists(WATCHLIST_FILE_PATH):
        save_watchlist(DEFAULT_WATCHLIST_DATA)
        return DEFAULT_WATCHLIST_DATA.copy()

    try:
        with open(WATCHLIST_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_WATCHLIST_DATA.copy()
            data.setdefault("us", [])
            data.setdefault("kr", [])
            return data
    except Exception as e:
        logger.error(f"Failed to load watchlist: {e}")
        return DEFAULT_WATCHLIST_DATA.copy()


def save_watchlist(data: Dict[str, List[str]]) -> bool:
    """Save watchlist dictionary to JSON file."""
    try:
        with open(WATCHLIST_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save watchlist: {e}")
        return False


def get_watchlist(market: str = "all") -> List[str]:
    """Get list of symbols for given market ('us', 'kr', or 'all')."""
    data = load_watchlist()
    if market == "us":
        return data.get("us", [])
    elif market == "kr":
        return data.get("kr", [])
    return data.get("us", []) + data.get("kr", [])


def add_to_watchlist(query: str) -> Tuple[bool, str, str]:
    """
    Add stock to watchlist. Automatically determines whether it's KRX or US.

    Returns:
        Tuple[bool, str, str]: (success, market, message)
    """
    from kr_bot.fetcher import find_kr_ticker_code, get_kr_stock_data
    from us_bot.fetcher import get_us_stock_data

    query = query.strip()
    if not query:
        return False, "", "⚠️ 추가할 종목명을 입력해주세요."

    data = load_watchlist()

    # 1. Check if it is a KRX stock (name or 6-digit code)
    kr_code = find_kr_ticker_code(query)
    if kr_code:
        if kr_code in data["kr"]:
            return False, "kr", f"ℹ️ **국내 종목({kr_code})**은 이미 관심종목에 등록되어 있습니다."
        
        # Verify valid data
        _, val = get_kr_stock_data(kr_code, days=30)
        name = val.get("name", kr_code)
        data["kr"].append(kr_code)
        save_watchlist(data)
        return True, "kr", f"✅ 국내 관심종목에 **{name} ({kr_code})**을(를) 추가했습니다!"

    # 2. Check if it is a US stock
    us_ticker = query.upper()
    df, val = get_us_stock_data(us_ticker, period="1mo")
    if df is not None and not df.empty:
        if us_ticker in data["us"]:
            return False, "us", f"ℹ️ **미국 종목({us_ticker})**은 이미 관심종목에 등록되어 있습니다."
        
        name = val.get("name", us_ticker)
        data["us"].append(us_ticker)
        save_watchlist(data)
        return True, "us", f"✅ 미국 관심종목에 **{name} ({us_ticker})**을(를) 추가했습니다!"

    return False, "", f"❌ **'{query}'** 종목을 찾을 수 없습니다. (종목코드 또는 영문 티커를 확인해주세요.)"


def remove_from_watchlist(query: str) -> Tuple[bool, str]:
    """
    Remove stock from watchlist.

    Returns:
        Tuple[bool, str]: (success, message)
    """
    from kr_bot.fetcher import find_kr_ticker_code

    query = query.strip()
    if not query:
        return False, "⚠️ 삭제할 종목명을 입력해주세요."

    data = load_watchlist()

    # Check KRX
    kr_code = find_kr_ticker_code(query)
    if kr_code and kr_code in data["kr"]:
        data["kr"].remove(kr_code)
        save_watchlist(data)
        return True, f"🗑️ 국내 관심종목에서 **{query} ({kr_code})**을(를) 삭제했습니다."

    # Check US
    us_ticker = query.upper()
    if us_ticker in data["us"]:
        data["us"].remove(us_ticker)
        save_watchlist(data)
        return True, f"🗑️ 미국 관심종목에서 **{us_ticker}**을(를) 삭제했습니다."

    return False, f"⚠️ 관심종목 목록에서 **'{query}'**을(를) 찾을 수 없습니다."


def format_watchlist_summary() -> str:
    """Format current watchlist into Markdown string."""
    from kr_bot.fetcher import find_kr_ticker_code
    from pykrx import stock

    data = load_watchlist()
    us_stocks = data.get("us", [])
    kr_stocks = data.get("kr", [])

    lines = ["⭐ **[내 등록 관심종목 목록]**", "-" * 35]

    lines.append("🇺🇸 **미국 주식**:")
    if us_stocks:
        lines.append("• " + ", ".join([f"`{s}`" for s in us_stocks]))
    else:
        lines.append("• 등록된 종목이 없습니다.")

    lines.append("\n🇰🇷 **국내 주식**:")
    if kr_stocks:
        kr_items = []
        for code in kr_stocks:
            name = code
            try:
                if stock is not None:
                    n = stock.get_market_ticker_name(code)
                    if n:
                        name = n
            except Exception:
                pass
            kr_items.append(f"{name}(`{code}`)")
        lines.append("• " + ", ".join(kr_items))
    else:
        lines.append("• 등록된 종목이 없습니다.")

    lines.append("\n" + "-" * 35)
    lines.append("💡 **관리 팁**:")
    lines.append("• 추가: `/add <종목명/티커>` (예: `/add MSFT`, `/add 카카오`)")
    lines.append("• 삭제: `/del <종목명/티커>` (예: `/del TSLA`, `/del 삼성전자`)")

    return "\n".join(lines)
