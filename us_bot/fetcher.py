"""
US Stock data fetcher module using yfinance.
Fetches historical daily bars and valuation metrics (PER, PBR, ROE).
"""
import yfinance as yf
import pandas as pd
from typing import Dict, Any, Tuple, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_us_stock_data(ticker_symbol: str, period: str = "6mo") -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """
    Fetch historical daily OHLCV data and valuation metrics for a given US stock ticker.

    Args:
        ticker_symbol: Stock ticker (e.g. 'AAPL', 'NVDA', 'TSLA').
        period: Historical period to fetch (default: '6mo').

    Returns:
        Tuple[Optional[pd.DataFrame], Dict[str, Any]]: (historical_df, valuation_dict)
    """
    ticker_symbol = ticker_symbol.strip().upper()
    try:
        ticker = yf.Ticker(ticker_symbol)
        df = ticker.history(period=period)
        
        if df.empty:
            logger.warning(f"No historical data returned for {ticker_symbol}")
            return None, {"ticker": ticker_symbol, "error": "No historical data"}

        # Fetch valuation metrics safely
        info = {}
        try:
            info = ticker.info or {}
        except Exception as e:
            logger.warning(f"Failed to fetch ticker info for {ticker_symbol}: {e}")

        trailing_pe = info.get("trailingPE")
        forward_pe = info.get("forwardPE")
        pbr = info.get("priceToBook")
        roe = info.get("returnOnEquity")
        short_name = info.get("shortName") or info.get("longName") or ticker_symbol

        pe_val = None
        if isinstance(trailing_pe, (int, float)) and trailing_pe > 0:
            pe_val = round(trailing_pe, 2)
        elif isinstance(forward_pe, (int, float)) and forward_pe > 0:
            pe_val = round(forward_pe, 2)

        valuations = {
            "ticker": ticker_symbol,
            "name": short_name,
            "currency": info.get("currency", "USD"),
            "pe": pe_val,
            "forward_pe": round(forward_pe, 2) if isinstance(forward_pe, (int, float)) and forward_pe > 0 else None,
            "pbr": round(pbr, 2) if isinstance(pbr, (int, float)) else None,
            "roe": round(roe * 100, 2) if isinstance(roe, (int, float)) else None,
            "market_cap": info.get("marketCap"),
        }

        return df, valuations

    except Exception as e:
        logger.error(f"Error fetching US stock data for {ticker_symbol}: {e}")
        return None, {"ticker": ticker_symbol, "error": str(e)}


def get_multiple_us_stocks(tickers: List[str], period: str = "6mo") -> Dict[str, Dict[str, Any]]:
    """
    Fetch historical data and valuation metrics for multiple US stocks.

    Returns:
        Dict[ticker, {'df': pd.DataFrame, 'valuation': dict}]
    """
    results = {}
    for t in tickers:
        df, val = get_us_stock_data(t, period=period)
        results[t] = {
            "df": df,
            "valuation": val
        }
    return results
