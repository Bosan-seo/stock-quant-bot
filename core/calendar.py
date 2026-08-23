"""
Global Economic Calendar & Corporate Earnings D-Day Tracking Module.
Tracks major macroeconomic events (FOMC, CPI, NFP, BOK) and upcoming watchlist earnings dates.
"""
from datetime import datetime, date
from typing import Dict, Any, List, Optional
import yfinance as yf
import logging

from core.watchlist import get_watchlist

logger = logging.getLogger(__name__)

# Master Schedule of Major Global Economic Events
GLOBAL_ECONOMIC_EVENTS = [
    {"date": "2026-08-28", "name": "미국 7월 PCE 개인소비지출 물가지수", "importance": "⭐⭐⭐", "impact": "연준 금리 결정 핵심 지표"},
    {"date": "2026-09-04", "name": "미국 8월 비농업 고용보고서 (NFP)", "importance": "⭐⭐⭐", "impact": "고용시장 건전성 및 실업률"},
    {"date": "2026-09-10", "name": "미국 8월 소비자물가지수 (CPI)", "importance": "⭐⭐⭐", "impact": "인플레이션 추세 점검"},
    {"date": "2026-09-16", "name": "미국 FOMC 기준금리 결정 및 점도표", "importance": "⭐⭐⭐⭐⭐", "impact": "글로벌 유동성 및 금리 피벗"},
    {"date": "2026-09-24", "name": "한국은행 금융통화위원회 (금통위)", "importance": "⭐⭐⭐⭐", "impact": "국내 기준금리 결정"},
    {"date": "2026-10-08", "name": "미국 9월 소비자물가지수 (CPI)", "importance": "⭐⭐⭐", "impact": "물가 안정화 여부"},
    {"date": "2026-11-04", "name": "미국 FOMC 기준금리 결정", "importance": "⭐⭐⭐⭐⭐", "impact": "연말 금리 정책 경로"},
    {"date": "2026-12-16", "name": "미국 FOMC 올해 마지막 금리 결정", "importance": "⭐⭐⭐⭐⭐", "impact": "내년 통화정책 가이던스"},
]


def get_upcoming_economic_events(limit: int = 5) -> List[Dict[str, Any]]:
    """
    Get upcoming global macroeconomic events sorted by nearest D-Day.
    """
    today = datetime.now().date()
    upcoming = []

    for ev in GLOBAL_ECONOMIC_EVENTS:
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        diff_days = (ev_date - today).days

        if diff_days >= 0:
            d_day_str = "D-Day (오늘!)" if diff_days == 0 else f"D-{diff_days}"
            upcoming.append({
                "date": ev["date"],
                "name": ev["name"],
                "importance": ev["importance"],
                "impact": ev["impact"],
                "days_left": diff_days,
                "d_day": d_day_str,
            })

    upcoming.sort(key=lambda x: x["days_left"])
    return upcoming[:limit]


def get_watchlist_earnings_schedule() -> List[Dict[str, Any]]:
    """
    Fetch upcoming earnings report dates for stocks in the watchlist via yfinance.
    """
    today = datetime.now().date()
    us_watchlist = get_watchlist("us")
    earnings_list = []

    for ticker in us_watchlist:
        try:
            t = yf.Ticker(ticker)
            cal = t.calendar
            if cal is not None and not cal.empty:
                # Typically row 0 contains Earnings Date
                earning_val = None
                if "Earnings Date" in cal.index:
                    earning_val = cal.loc["Earnings Date"].iloc[0]
                elif isinstance(cal, dict) and "Earnings Date" in cal:
                    earning_val = cal["Earnings Date"][0]

                if earning_val:
                    if hasattr(earning_val, "date"):
                        e_date = earning_val.date()
                    else:
                        e_date = datetime.strptime(str(earning_val)[:10], "%Y-%m-%d").date()

                    diff = (e_date - today).days
                    if diff >= 0:
                        d_day_str = "D-Day (오늘!)" if diff == 0 else f"D-{diff}"
                        earnings_list.append({
                            "ticker": ticker,
                            "date": e_date.strftime("%Y-%m-%d"),
                            "days_left": diff,
                            "d_day": d_day_str,
                        })
        except Exception as e:
            logger.debug(f"Earnings fetch note for {ticker}: {e}")

    earnings_list.sort(key=lambda x: x["days_left"])
    return earnings_list


def format_economic_calendar_report() -> str:
    """
    Format upcoming economic events and earnings calendar into a Telegram Markdown report.
    """
    now_str = datetime.now().strftime("%Y-%m-%d")
    lines = [
        f"📅 **[글로벌 주요 경제 일정 & 실적 캘린더]**",
        f"🕒 기준일자: `{now_str}`",
        "=" * 35,
    ]

    # 1. Macro Economic Events
    events = get_upcoming_economic_events(limit=6)
    lines.append("\n🌐 **주요 거시경제 지표 및 중앙은행 발표 일정**")
    lines.append("-" * 35)
    if events:
        for ev in events:
            lines.append(
                f"• 🚨 **[{ev['d_day']}]** `{ev['date']}`\n"
                f"  **{ev['name']}** {ev['importance']}\n"
                f"  └ 💬 *{ev['impact']}*"
            )
    else:
        lines.append("• 예정된 주요 경제 일정이 없습니다.")

    # 2. Watchlist Earnings Schedule
    lines.append("\n\n📊 **내 관심종목 차기 실적(어닝) 발표 D-Day**")
    lines.append("-" * 35)
    earnings = get_watchlist_earnings_schedule()
    if earnings:
        for e in earnings:
            lines.append(
                f"• 🔔 **[{e['d_day']}]** `{e['date']}` : 🇺🇸 **{e['ticker']}** 실적 발표 예정"
            )
    else:
        lines.append("• 관심종목 중 30일 이내 실적 발표 예정 종목이 없습니다.")
        lines.append("• `/add <티커>`로 관심종목을 등록해두면 어닝 디데이를 자동 추적합니다!")

    return "\n".join(lines)
