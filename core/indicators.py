"""
Technical indicators module using pandas and numpy.
Provides calculations for SMA, RSI, and MACD.
"""
import pandas as pd
import numpy as np
from typing import Union, Tuple


def calculate_sma(data: Union[pd.Series, pd.DataFrame], period: int = 20, column: str = 'Close') -> pd.Series:
    """
    Calculate Simple Moving Average (SMA).

    Args:
        data: pandas Series of prices or DataFrame containing price column.
        period: moving average period (default: 20).
        column: target price column name if DataFrame is provided.

    Returns:
        pd.Series: SMA values.
    """
    series = data[column] if isinstance(data, pd.DataFrame) else data
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    return series.rolling(window=period, min_periods=period).mean()


def calculate_rsi(data: Union[pd.Series, pd.DataFrame], period: int = 14, column: str = 'Close') -> pd.Series:
    """
    Calculate Relative Strength Index (RSI) using exponential smoothing (Wilder's method).

    Args:
        data: pandas Series of prices or DataFrame containing price column.
        period: RSI period (default: 14).
        column: target price column name if DataFrame is provided.

    Returns:
        pd.Series: RSI values (0-100).
    """
    series = data[column] if isinstance(data, pd.DataFrame) else data
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]
    delta = series.diff()

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    # Wilder's Exponential Smoothing
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    
    # Where avg_loss was 0, RSI is 100; where avg_gain was 0 and avg_loss > 0, RSI is 0
    fill_vals = pd.Series(np.where(avg_gain > 0, 100.0, 50.0), index=rsi.index)
    rsi = rsi.fillna(fill_vals)
    return rsi


def calculate_macd(
    data: Union[pd.Series, pd.DataFrame],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
    column: str = 'Close'
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Moving Average Convergence Divergence (MACD).

    Args:
        data: pandas Series of prices or DataFrame containing price column.
        fast: fast EMA period (default: 12).
        slow: slow EMA period (default: 26).
        signal: signal line EMA period (default: 9).
        column: target price column name if DataFrame is provided.

    Returns:
        Tuple[pd.Series, pd.Series, pd.Series]: (macd_line, signal_line, macd_histogram)
    """
    series = data[column] if isinstance(data, pd.DataFrame) else data
    if isinstance(series, pd.DataFrame):
        series = series.iloc[:, 0]

    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()

    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - signal_line

    return macd_line, signal_line, macd_hist


def add_technical_indicators(df: pd.DataFrame, price_col: str = 'Close') -> pd.DataFrame:
    """
    Add SMA20, RSI14, and MACD indicators directly to the DataFrame.

    Args:
        df: pandas DataFrame containing historical price data.
        price_col: name of the price column (default: 'Close').

    Returns:
        pd.DataFrame: DataFrame with new indicator columns added.
    """
    df = df.copy()
    if price_col not in df.columns:
        # Check case-insensitive match
        matched = [col for col in df.columns if str(col).lower() == price_col.lower()]
        if matched:
            price_col = matched[0]
        else:
            raise KeyError(f"Price column '{price_col}' not found in DataFrame columns: {list(df.columns)}")

    df['SMA20'] = calculate_sma(df, period=20, column=price_col)
    df['RSI14'] = calculate_rsi(df, period=14, column=price_col)
    
    macd_line, signal_line, macd_hist = calculate_macd(df, fast=12, slow=26, signal=9, column=price_col)
    df['MACD'] = macd_line
    df['MACD_Signal'] = signal_line
    df['MACD_Hist'] = macd_hist

    return df
