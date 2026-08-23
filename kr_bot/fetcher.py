"""
Korean Stock data fetcher module using comprehensive KRX master list,
Naver Finance Realtime & Integration APIs, and yfinance fallback.
"""
import os
import json
import pandas as pd
import requests
from io import StringIO
from datetime import datetime, timedelta
from typing import Dict, Any, Tuple, List, Optional
import logging

try:
    from pykrx import stock
except ImportError:
    stock = None

try:
    import yfinance as yf
except ImportError:
    yf = None

logger = logging.getLogger(__name__)

KRX_MASTER_JSON_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "core",
    "krx_tickers.json"
)

# Column name normalization map for pykrx OHLCV DataFrames
KRX_OHLCV_RENAME_MAP = {
    "시가": "Open",
    "고가": "High",
    "저가": "Low",
    "종가": "Close",
    "거래량": "Volume",
    "거래대금": "Value",
    "등락률": "ChangePct",
}

_KRX_NAME_TO_CODE: Dict[str, str] = {}
_KRX_CODE_TO_NAME: Dict[str, str] = {}


def load_krx_master_mapping() -> Dict[str, str]:
    """
    Load all 2,800+ KRX listed companies and aliases from master JSON or download on-demand.
    """
    global _KRX_NAME_TO_CODE, _KRX_CODE_TO_NAME
    if _KRX_NAME_TO_CODE:
        return _KRX_NAME_TO_CODE

    if os.path.exists(KRX_MASTER_JSON_PATH):
        try:
            with open(KRX_MASTER_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                _KRX_NAME_TO_CODE = data
                for k, v in data.items():
                    if len(k) != 6 or not k.isdigit():
                        _KRX_CODE_TO_NAME[v] = k
                return _KRX_NAME_TO_CODE
        except Exception as e:
            logger.warning(f"Failed to load krx_tickers.json: {e}")

    # On-demand fallback download from KRX KIND
    try:
        url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.encoding = "euc-kr"
        df = pd.read_html(StringIO(resp.text), header=0)[0]
        mapping = {}
        for _, row in df.iterrows():
            name = str(row["회사명"]).strip()
            code = str(row["종목코드"]).strip().zfill(6)
            mapping[name.lower().replace(" ", "")] = code
            mapping[name] = code
            _KRX_CODE_TO_NAME[code] = name
        _KRX_NAME_TO_CODE = mapping
        return _KRX_NAME_TO_CODE
    except Exception as e:
        logger.error(f"Failed to fetch KRX master from KIND: {e}")
        return {}


def find_kr_ticker_code(query: str) -> Optional[str]:
    """
    Find 6-digit KRX ticker code by company name or return code if already valid.
    Implements strict exact match -> prefix match -> safe substring match.
    """
    import re

    query = query.strip()
    if not query:
        return None

    # If already a 6-digit code
    if len(query) == 6 and query.isdigit():
        return query

    mapping = load_krx_master_mapping()
    clean_query = query.lower().replace(" ", "")

    # 1. Exact match (case & space-insensitive)
    if clean_query in mapping:
        return mapping[clean_query]

    # 2. Match with original query
    if query in mapping:
        return mapping[query]

    # 3. Prefix match (Company name starts with query, e.g. '삼성' -> '삼성전자')
    for name, code in mapping.items():
        if name.startswith(clean_query) and len(clean_query) >= 2:
            return code

    # 4. Safe Partial match (Only allow if query contains Korean or is at least 3 chars)
    has_korean = bool(re.search(r"[가-힣]", clean_query))
    if has_korean or len(clean_query) >= 3:
        candidates = []
        for name, code in mapping.items():
            if clean_query in name:
                candidates.append((len(name), code))

        if candidates:
            candidates.sort(key=lambda x: x[0])
            return candidates[0][1]

    return None


def fetch_naver_fundamentals(ticker_code: str) -> Dict[str, Any]:
    """
    Fetch accurate, realtime price, change, and financial metrics from Naver Stock APIs.
    """
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    result = {}

    def clean_num(val_str: Optional[str]) -> Optional[float]:
        if not val_str:
            return None
        val_clean = str(val_str).replace("배", "").replace("원", "").replace("%", "").replace(",", "").strip()
        try:
            return float(val_clean)
        except ValueError:
            return None

    # 1. Fetch Realtime Basic Quote
    try:
        basic_url = f"https://m.stock.naver.com/api/stock/{ticker_code}/basic"
        b_resp = requests.get(basic_url, headers=headers, timeout=4)
        if b_resp.status_code == 200:
            b_data = b_resp.json()
            result["name"] = b_data.get("stockName")
            result["current_price"] = clean_num(b_data.get("closePrice") or b_data.get("nowPrice"))
            result["change_price"] = clean_num(b_data.get("compareToPreviousClosePrice"))
            result["change_rate"] = clean_num(b_data.get("fluctuationsRatio"))
            result["change_type"] = b_data.get("compareToPreviousPrice", {}).get("name", "SAME")  # RISING / FALLING / SAME
            result["traded_at"] = b_data.get("localTradedAt")
    except Exception as e:
        logger.debug(f"Naver basic quote fetch note for {ticker_code}: {e}")

    # 2. Fetch Integration Fundamentals & Ranges
    try:
        integ_url = f"https://m.stock.naver.com/api/stock/{ticker_code}/integration"
        i_resp = requests.get(integ_url, headers=headers, timeout=4)
        if i_resp.status_code == 200:
            i_data = i_resp.json()
            if not result.get("name"):
                result["name"] = i_data.get("stockName")
            infos = {item.get("key"): item.get("value") for item in i_data.get("totalInfos", [])}

            result["prev_close"] = clean_num(infos.get("전일종가"))
            result["open_price"] = clean_num(infos.get("시가"))
            result["high_price"] = clean_num(infos.get("고가"))
            result["low_price"] = clean_num(infos.get("저가"))
            result["volume"] = int(clean_num(infos.get("거래량")) or 0)
            result["market_cap"] = infos.get("시가총액", "N/A")
            result["foreign_rate"] = infos.get("외국인소진율", "N/A")
            result["week52_high"] = infos.get("52주 최고", "N/A")
            result["week52_low"] = infos.get("52주 최저", "N/A")
            result["per"] = clean_num(infos.get("PER"))
            result["pbr"] = clean_num(infos.get("PBR"))
            result["eps"] = clean_num(infos.get("EPS"))
            result["bps"] = clean_num(infos.get("BPS"))
            result["div"] = clean_num(infos.get("배당수익률"))
    except Exception as e:
        logger.debug(f"Naver integration fetch note for {ticker_code}: {e}")

    return result


def get_kr_stock_data(ticker_code: str, days: int = 180) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Fetch historical daily OHLCV data and valuation metrics for a given KRX stock code.
    """
    ticker_code = ticker_code.strip()
    end_date = datetime.now().strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

    # 1. Fetch Company Name from Master
    load_krx_master_mapping()
    name = _KRX_CODE_TO_NAME.get(ticker_code, ticker_code)

    # 2. Fetch Detailed Fundamentals from Naver API
    naver_info = fetch_naver_fundamentals(ticker_code)
    if naver_info.get("name"):
        name = naver_info["name"]

    # 3. Fetch OHLCV Price Data via pykrx
    df = None
    if stock is not None:
        try:
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker_code)
            if df is not None and not df.empty:
                df = df.rename(columns=KRX_OHLCV_RENAME_MAP)
                df["Close"] = pd.to_numeric(df["Close"], errors="coerce")
        except Exception as e:
            logger.warning(f"pykrx OHLCV error for {ticker_code}: {e}")

    # Fallback to yfinance if pykrx OHLCV fails
    if (df is None or df.empty) and yf is not None:
        for suffix in [".KS", ".KQ"]:
            try:
                yf_ticker = f"{ticker_code}{suffix}"
                yf_df = yf.Ticker(yf_ticker).history(period=f"{days}d")
                if not yf_df.empty:
                    df = yf_df
                    break
            except Exception:
                pass

    if df is None or df.empty:
        return None, {"ticker": ticker_code, "name": name, "error": "No price data available"}

    # 4. Construct Comprehensive Valuations & Financials Dict
    valuations = {
        "ticker": ticker_code,
        "name": name,
        "current_price": naver_info.get("current_price"),
        "change_price": naver_info.get("change_price"),
        "change_rate": naver_info.get("change_rate"),
        "change_type": naver_info.get("change_type"),
        "traded_at": naver_info.get("traded_at"),
        "prev_close": naver_info.get("prev_close"),
        "market_cap": naver_info.get("market_cap", "N/A"),
        "foreign_rate": naver_info.get("foreign_rate", "N/A"),
        "week52_high": naver_info.get("week52_high", "N/A"),
        "week52_low": naver_info.get("week52_low", "N/A"),
        "open_price": naver_info.get("open_price"),
        "high_price": naver_info.get("high_price"),
        "low_price": naver_info.get("low_price"),
        "volume": naver_info.get("volume"),
        "per": naver_info.get("per"),
        "pbr": naver_info.get("pbr"),
        "eps": naver_info.get("eps"),
        "bps": naver_info.get("bps"),
        "div": naver_info.get("div"),
    }

    # If Naver failed, try yfinance fundamentals as fallback
    if valuations["per"] is None and yf is not None:
        for suffix in [".KS", ".KQ"]:
            try:
                yf_info = yf.Ticker(f"{ticker_code}{suffix}").info or {}
                if yf_info:
                    pe = yf_info.get("trailingPE") or yf_info.get("forwardPE")
                    pbr = yf_info.get("priceToBook")
                    div = yf_info.get("dividendYield")
                    if pe:
                        valuations["per"] = round(float(pe), 2)
                    if pbr:
                        valuations["pbr"] = round(float(pbr), 2)
                    if div:
                        div_val = float(div)
                        valuations["div"] = round(div_val * 100 if div_val < 1.0 else div_val, 2)
                    break
            except Exception:
                pass

    return df, valuations


def get_multiple_kr_stocks(tickers: List[str], days: int = 180) -> Dict[str, Dict[str, Any]]:
    """
    Fetch historical data and valuations for multiple KRX stocks.
    """
    results = {}
    for t in tickers:
        df, val = get_kr_stock_data(t, days=days)
        results[t] = {
            "df": df,
            "valuation": val
        }
    return results
