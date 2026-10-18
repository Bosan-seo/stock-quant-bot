"""
Deterministic Quant Pre-computation Engine.
Computes technical indicators, volatility (ATR14), Bollinger Bands, RVOL,
directional momentum (RSI 3d Delta, MACD slope), objective support/resistance/stop-loss,
and mode-weighted quantitative scores (0~100) prior to LLM invocation.
Enforces the Zero-Calculation Rule to prevent LLM hallucinations.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
import numpy as np
import pandas as pd


@dataclass
class QuantMetrics:
    ticker: str
    name: str
    currency: str
    price: float
    change_pct: float
    sma20: float
    sma20_gap_pct: float       # 이격도 (%)
    rsi14: float
    rsi_delta_3d: float        # 3일 전 대비 RSI 변화량
    macd: float
    macd_signal: float
    macd_hist_slope: str       # 히스토그램 추세 (확대/축소/골든크로스/데드크로스)
    rvol: float                # 20일 평균 대비 거래량 비율 (배)
    atr14: float               # 변동성 지표
    support_1: float           # 1차 기술적 지지선 (ATR 및 볼린저 하단 기반)
    resistance_1: float        # 1차 기술적 저항선/목표가 (ATR 및 볼린저 상단 기반)
    stop_loss: float           # 권장 손절선 (현재가 - 2*ATR)
    per_str: str
    pbr_str: str
    div_yield_str: str
    quant_score: int           # 0 ~ 100 정량 점수
    recommended_grade: str     # 파이썬이 확정한 투자 등급 태그


def compute_quant_metrics(
    df: pd.DataFrame,
    ticker: str,
    name: str,
    fundamentals: Dict[str, Any],
    mode: str = "standard",
    currency: str = "$"
) -> QuantMetrics:
    """
    df: DataFrame containing at least 25 historical daily bars (Open, High, Low, Close, Volume)
    fundamentals: dict with keys 'per', 'pbr', 'div_yield'
    mode: 'standard', 'conservative', 'momentum', 'macro'
    """
    # Normalize column names to Title Case
    col_map = {c.lower(): c for c in df.columns}
    close_col = col_map.get("close", "Close")
    high_col = col_map.get("high", "High")
    low_col = col_map.get("low", "Low")
    vol_col = col_map.get("volume", "Volume")

    close = df[close_col].astype(float)
    high = df[high_col].astype(float) if high_col in df.columns else close
    low = df[low_col].astype(float) if low_col in df.columns else close
    vol = df[vol_col].astype(float) if vol_col in df.columns else pd.Series(1.0, index=df.index)

    price = float(close.iloc[-1])
    prev_price = float(close.iloc[-2]) if len(close) >= 2 else price
    change_pct = round(((price - prev_price) / prev_price) * 100, 2) if prev_price > 0 else 0.0

    # 1. 이동평균 및 볼린저밴드 (20, 2)
    sma20_series = close.rolling(20, min_periods=5).mean()
    std20_series = close.rolling(20, min_periods=5).std().fillna(0)
    sma20 = float(sma20_series.iloc[-1])
    bb_upper = float(sma20 + 2 * std20_series.iloc[-1])
    bb_lower = float(sma20 - 2 * std20_series.iloc[-1])
    sma20_gap_pct = round(((price - sma20) / sma20) * 100, 2) if sma20 > 0 else 0.0

    # 2. RSI(14) 및 3일 방향성(Delta)
    delta = close.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi_series = 100 - (100 / (1 + rs))
    rsi_series = rsi_series.fillna(50.0)
    rsi14 = round(float(rsi_series.iloc[-1]), 1)
    rsi_prev_3d = float(rsi_series.iloc[-4]) if len(rsi_series) >= 4 else float(rsi_series.iloc[0])
    rsi_delta_3d = round(float(rsi14 - rsi_prev_3d), 1)

    # 3. MACD (12, 26, 9) 및 히스토그램 기울기
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd_series = ema12 - ema26
    signal_series = macd_series.ewm(span=9, adjust=False).mean()
    hist_series = macd_series - signal_series

    macd_val = round(float(macd_series.iloc[-1]), 2)
    sig_val = round(float(signal_series.iloc[-1]), 2)
    hist_now = float(hist_series.iloc[-1])
    hist_prev = float(hist_series.iloc[-2]) if len(hist_series) >= 2 else hist_now

    if hist_prev <= 0 and hist_now > 0:
        macd_hist_slope = "골든크로스 발생(상승 추세 전환)"
    elif hist_prev >= 0 and hist_now < 0:
        macd_hist_slope = "데드크로스 발생(하락 조정 전환)"
    elif hist_now > 0 and hist_now > hist_prev:
        macd_hist_slope = "양(+)봉 확대(상승 가속)"
    elif hist_now > 0 and hist_now <= hist_prev:
        macd_hist_slope = "양(+)봉 축소(상승 탄력 둔화)"
    elif hist_now < 0 and hist_now > hist_prev:
        macd_hist_slope = "음(-)봉 축소(하락 진정/반등 모색)"
    else:
        macd_hist_slope = "음(-)봉 확대(하락 모멘텀 심화)"

    # 4. RVOL (상대 거래량) & ATR(14)
    if len(vol) >= 21:
        vol_ma20 = float(vol.iloc[-21:-1].mean())
    else:
        vol_ma20 = float(vol.mean())
    rvol = round(float(vol.iloc[-1]) / vol_ma20, 2) if vol_ma20 > 0 else 1.0

    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    atr14_series = tr.rolling(14, min_periods=3).mean().fillna(price * 0.02)
    atr14 = float(atr14_series.iloc[-1])

    # 5. ATR 및 볼린저밴드 기반 객관적 지지/저항/손절가
    if price >= sma20:
        support_1 = round(max(bb_lower, min(sma20, price - 1.2 * atr14)), 2)
        resistance_1 = round(min(bb_upper, price + 1.8 * atr14), 2)
    else:
        support_1 = round(max(bb_lower, price - 1.2 * atr14), 2)
        resistance_1 = round(sma20, 2)
    stop_loss = round(max(0.01, price - 2.0 * atr14), 2)

    # 6. 밸류에이션 결측치 안전 포맷팅
    per = fundamentals.get("per")
    pbr = fundamentals.get("pbr")
    div_y = fundamentals.get("div_yield")
    
    # Clean possible string formats
    try:
        if per is not None:
            per = float(str(per).replace("배", "").replace(",", "").strip())
    except Exception:
        per = None
    try:
        if pbr is not None:
            pbr = float(str(pbr).replace("배", "").replace(",", "").strip())
    except Exception:
        pbr = None
    try:
        if div_y is not None:
            div_y = float(str(div_y).replace("%", "").replace(",", "").strip())
    except Exception:
        div_y = None

    per_str = f"{per:.1f}배" if per and per > 0 else "N/A(적자 또는 미집계)"
    pbr_str = f"{pbr:.2f}배" if pbr and pbr > 0 else "N/A"
    div_yield_str = f"{div_y:.2f}%" if div_y is not None and div_y >= 0 else "0.0%"

    # 7. 모드별 가중치가 반영된 Deterministic Quant Score (0~100)
    tech_score = 50
    if price > sma20:
        tech_score += 15
    if hist_now > hist_prev:
        tech_score += 15
    if 40 <= rsi14 <= 65 and rsi_delta_3d > 0:
        tech_score += 10
    elif rsi14 < 35 and rsi_delta_3d > 0:
        tech_score += 15  # 과매도 반등 모멘텀
    elif rsi14 > 75:
        tech_score -= 15  # 과열 부담
    if rvol >= 1.4 and change_pct > 0:
        tech_score += 10

    val_score = 50
    if per and 0 < per < 15:
        val_score += 20
    elif per and per > 40:
        val_score -= 10
    if pbr and 0 < pbr < 1.2:
        val_score += 15
    if div_y and div_y >= 3.5:
        val_score += 15

    mode_lower = mode.lower()
    if mode_lower == "conservative":
        final_score = int(np.clip(tech_score * 0.35 + val_score * 0.65, 0, 100))
    elif mode_lower == "momentum":
        final_score = int(np.clip(tech_score * 0.85 + val_score * 0.15, 0, 100))
    else:  # standard & macro
        final_score = int(np.clip(tech_score * 0.60 + val_score * 0.40, 0, 100))

    if final_score >= 80:
        grade = "🟢 **[적극 매수 / 상승 유력]**"
    elif final_score >= 65:
        grade = "🔵 **[분할 매수 / 눌림목 관심]**"
    elif final_score >= 45:
        grade = "⚖️ **[중립 / 관망 권고]**"
    elif final_score >= 30:
        grade = "🟡 **[비중 축소 / 리스크 관리]**"
    else:
        grade = "🔴 **[보수적 접근 / 손절 고려]**"

    return QuantMetrics(
        ticker=ticker,
        name=name,
        currency=currency,
        price=price,
        change_pct=change_pct,
        sma20=round(sma20, 2),
        sma20_gap_pct=sma20_gap_pct,
        rsi14=rsi14,
        rsi_delta_3d=rsi_delta_3d,
        macd=macd_val,
        macd_signal=sig_val,
        macd_hist_slope=macd_hist_slope,
        rvol=rvol,
        atr14=round(atr14, 2),
        support_1=support_1,
        resistance_1=resistance_1,
        stop_loss=stop_loss,
        per_str=per_str,
        pbr_str=pbr_str,
        div_yield_str=div_yield_str,
        quant_score=final_score,
        recommended_grade=grade
    )
