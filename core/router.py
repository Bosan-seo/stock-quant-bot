"""
Smart query classification and routing module for KRX vs US stock searches.
"""
import re
from typing import Tuple

# English aliases specifically for Korean conglomerates
KR_ENGLISH_ALIASES = {
    "posco": "005490",
    "naver": "035420",
    "kakao": "035720",
    "samsung": "005930",
    "hynix": "000660",
    "kt": "030200",
    "skt": "017670",
    "lg": "003550",
    "kt&g": "033780",
    "celltrion": "068270",
}


def route_stock_query(query_text: str) -> Tuple[str, str]:
    """
    Classify query into ('KR', target) or ('US', target) to prevent misrouting.

    Returns:
        Tuple[str, str]: ('KR' | 'US' | 'UNKNOWN', cleaned_target)
    """
    clean = query_text.strip()
    if not clean:
        return "UNKNOWN", ""

    # 1. Check explicit prefixes: 'us:AAPL', 'kr:삼성전자', '/us TSLA', '/kr 005930'
    lower_clean = clean.lower()
    if lower_clean.startswith("us:") or lower_clean.startswith("us "):
        target = clean[3:].strip().upper()
        return "US", target
    if lower_clean.startswith("kr:") or lower_clean.startswith("kr "):
        target = clean[3:].strip()
        return "KR", target

    # 2. 6-digit numeric string -> KRX stock code (e.g., '005930', '058470')
    if len(clean) == 6 and clean.isdigit():
        return "KR", clean

    # 3. Known Korean English conglomerate names (e.g. 'posco', 'naver')
    if lower_clean in KR_ENGLISH_ALIASES:
        return "KR", KR_ENGLISH_ALIASES[lower_clean]

    # 4. If query contains ANY Korean character -> Route to KRX search
    has_korean = bool(re.search(r"[가-힣]", clean))
    if has_korean:
        return "KR", clean

    # 5. Pure alphanumeric ticker (1~6 chars, e.g. 'AAPL', 'ON', 'AI', 'KO', 'SO', 'OPEN', 'NVDA')
    # Route directly to US stock pipeline
    if re.match(r"^[A-Za-z0-9\.\-\=]{1,6}$", clean):
        return "US", clean.upper()

    # Default fallback
    return "KR", clean
