"""
Core package for stock bot project.
Provides shared technical indicators, macroeconomic data fetcher, and notification modules.
"""
from core.indicators import calculate_sma, calculate_rsi, calculate_macd, add_technical_indicators
from core.macro import get_macro_indicators
from core.notifier import send_telegram_message
from core.watchlist import get_watchlist, add_to_watchlist, remove_from_watchlist, format_watchlist_summary

__all__ = [
    "calculate_sma",
    "calculate_rsi",
    "calculate_macd",
    "add_technical_indicators",
    "get_macro_indicators",
    "send_telegram_message",
    "get_watchlist",
    "add_to_watchlist",
    "remove_from_watchlist",
    "format_watchlist_summary",
]
