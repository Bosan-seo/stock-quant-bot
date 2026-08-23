"""
AI & Rule-based Quant Analysis Engine.
Generates a concise 3-line investment diagnosis and rating based on technical indicators and fundamentals.
Supports Google Gemini API with seamless fallback to rule-based quant scoring.
"""
import os
import json
import requests
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def _rule_based_quant_diagnosis(data: Dict[str, Any]) -> str:
    """
    High-precision rule-based quant scoring fallback.
    Evaluates:
      - Trend (SMA20 breakout/above/below)
      - Momentum (RSI oversold/overbought/neutral, MACD golden/dead cross)
      - Valuation (PER, PBR, Dividend Yield, ROE)
    """
    name = data.get("name", "종목")
    price = data.get("price", 0)
    change_pct = data.get("change_pct", 0)
    sma20 = data.get("sma20")
    prev_sma20 = data.get("prev_sma20")
    prev_close = data.get("prev_close")
    rsi14 = data.get("rsi14")
    macd = data.get("macd")
    macd_signal = data.get("macd_signal")
    per = data.get("per")
    pbr = data.get("pbr")
    div_yield = data.get("div_yield")
    roe = data.get("roe")

    score = 50  # Base neutral score (0 ~ 100)
    points = []
    risks = []

    # 1. Trend Evaluation (SMA20)
    if sma20 is not None and price is not None:
        if prev_sma20 and prev_close and prev_close < prev_sma20 and price >= sma20:
            score += 20
            points.append("20일 이평선 상향 돌파로 단기 상승 추세 전환")
        elif price >= sma20:
            score += 10
            points.append("20일선 상회 안착으로 안정적인 상승 지지력 확보")
        else:
            score -= 15
            risks.append("20일선 하회로 단기 매물대 소화 및 지지 확인 필요")

    # 2. Momentum Evaluation (RSI)
    if rsi14 is not None:
        if rsi14 <= 32:
            score += 15
            points.append(f"RSI({rsi14:.1f}) 기술적 과매도권으로 저가 반등 매수세 유입 기대")
        elif rsi14 >= 68:
            score -= 10
            risks.append(f"RSI({rsi14:.1f}) 단기 과열권으로 차익 실현 매물 출회 주의")
        else:
            points.append(f"RSI({rsi14:.1f}) 중립 구간에서 점진적 모멘텀 형성")

    # 3. MACD Cross
    if macd is not None and macd_signal is not None:
        if macd >= macd_signal:
            score += 10
            points.append("MACD 골든크로스 상승 추세 유지")
        else:
            score -= 10
            risks.append("MACD 데드크로스 진행으로 단기 조정 국면")

    # 4. Valuation Evaluation
    if per is not None and isinstance(per, (int, float)):
        if 0 < per <= 15:
            score += 10
            points.append(f"PER {per:.1f}배 수준으로 업종 대비 저평가 밸류에이션 매력")
        elif per > 50:
            score -= 10
            risks.append(f"PER {per:.1f}배로 고평가 부담이 있어 실적 성장 지속성 확인 필요")

    if div_yield is not None and isinstance(div_yield, (int, float)) and div_yield >= 3.0:
        score += 5
        points.append(f"배당수익률 {div_yield:.2f}%로 하방 안전마진 보유")

    # Determine Rating
    if score >= 75:
        rating = "🟢 **[적극 매수 / 상승 유력]**"
    elif score >= 60:
        rating = "🔵 **[분할 매수 / 눌림목 관심]**"
    elif score >= 45:
        rating = "⚖️ **[중립 / 관망 권고]**"
    elif score >= 35:
        rating = "🟡 **[비중 축소 / 리스크 관리]**"
    else:
        rating = "🔴 **[보수적 접근 / 손절 고려]**"

    b1 = points[0] if points else "현재 주가 지지선 테스트 진행 중"
    b2 = points[1] if len(points) > 1 else (risks[0] if risks else "거래량 동향과 수급 주체 추적 필요")
    b3 = risks[0] if risks and risks[0] != b2 else (points[2] if len(points) > 2 else "주요 지지선 이탈 시 손절가 설정 필수")

    return f"💡 **AI 퀀트 종합 진단**: {rating}\n• {b1}\n• {b2}\n• {b3}"


def generate_quant_opinion(stock_data: Dict[str, Any]) -> str:
    """
    Generate 3-line quant investment opinion using Gemini AI or Fallback.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _rule_based_quant_diagnosis(stock_data)

    name = stock_data.get("name", "종목")
    ticker = stock_data.get("ticker", "")
    price = stock_data.get("price", "N/A")
    change_pct = stock_data.get("change_pct", "0.0")
    sma20 = stock_data.get("sma20", "N/A")
    rsi14 = stock_data.get("rsi14", "N/A")
    macd = stock_data.get("macd", "N/A")
    macd_signal = stock_data.get("macd_signal", "N/A")
    per = stock_data.get("per", "N/A")
    pbr = stock_data.get("pbr", "N/A")
    div_yield = stock_data.get("div_yield", "N/A")

    prompt = f"""당신은 퀀트/기술적 분석 전문가입니다.
다음 주식 데이터를 바탕으로 텔레그램 리포트용 '3줄 요약 퀀트 진단 및 투자 의견'을 한국어로 작성해주세요.

[종목 정보]
• 종목명: {name} ({ticker})
• 현재가/등락률: {price} ({change_pct}%)
• 20일선: {sma20}
• RSI (14): {rsi14}
• MACD: {macd} / Signal {macd_signal}
• 밸류에이션: PER {per}, PBR {pbr}, 배당수익률 {div_yield}%

[작성 규칙]
1. 첫째 줄: 🟢 [적극 매수], 🔵 [분할 매수], ⚖️ [중립/관망], 🟡 [비중 축소] 중 1개 태그로 시작
2. 이어지는 3개의 불릿포인트(•)로 기술적 추세, 밸류에이션, 핵심 대응전략을 1문장씩 작성
3. 간결하고 명확하게 마크다운 형식으로 작성
"""

    for model in ["gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-flash"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 400}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=4)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    if text:
                        return f"💡 **AI 퀀트 종합 진단 (Gemini AI)**\n{text}"
        except Exception as e:
            logger.debug(f"Gemini {model} call note: {e}")
            continue

    # Fallback to rule-based engine
    return _rule_based_quant_diagnosis(stock_data)
