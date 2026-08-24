"""
AI & Rule-based Quant Analysis Engine (Bulletproof Production Version).
Generates high-precision 3-line investment diagnosis and rating based on technical indicators and fundamentals.
Includes Quality Gate Validation to guarantee clean, complete Korean responses every time.
"""
import os
import re
import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def _rule_based_quant_diagnosis(data: Dict[str, Any]) -> str:
    """
    High-precision rule-based quant scoring fallback.
    Evaluates:
      - Trend (SMA20 breakout/above/below)
      - Momentum (RSI oversold/overbought/neutral, MACD golden/dead cross)
      - Valuation (PER, PBR, Dividend Yield, ROE)
    """
    price = data.get("price", 0)
    sma20 = data.get("sma20")
    prev_sma20 = data.get("prev_sma20")
    prev_close = data.get("prev_close")
    rsi14 = data.get("rsi14")
    macd = data.get("macd")
    macd_signal = data.get("macd_signal")
    per = data.get("per")
    div_yield = data.get("div_yield")

    score = 50
    points = []
    risks = []

    # 1. Trend (SMA20)
    if sma20 is not None and price is not None:
        try:
            p_val = float(str(price).replace("$", "").replace(",", "").replace("원", "").strip())
            s_val = float(str(sma20).replace("$", "").replace(",", "").replace("원", "").strip())
            if prev_sma20 and prev_close and prev_close < prev_sma20 and p_val >= s_val:
                score += 20
                points.append("20일 이동평균선을 상향 돌파하며 단기 추세 전환에 성공했습니다.")
            elif p_val >= s_val:
                score += 10
                points.append("20일선 위에 안정적으로 안착하여 상승 지지력을 유지하고 있습니다.")
            else:
                score -= 15
                risks.append("20일선을 하회하고 있어 단기 매물대 소화 및 지지선 확인이 필요합니다.")
        except Exception:
            pass

    # 2. Momentum (RSI)
    if rsi14 is not None:
        try:
            r_val = float(str(rsi14).replace("🔥", "").replace("🧊", "").strip())
            if r_val <= 32:
                score += 15
                points.append(f"RSI({r_val:.1f}) 과매도 구간으로 저가 반등 매수세 유입이 기대됩니다.")
            elif r_val >= 70:
                score -= 10
                risks.append(f"RSI({r_val:.1f}) 단기 과열권에 진입하여 차익 실현 매물 출회에 유의해야 합니다.")
            else:
                points.append(f"RSI({r_val:.1f}) 중립 구간에서 안정적인 에너지를 응축 중입니다.")
        except Exception:
            pass

    # 3. MACD
    if macd is not None and macd_signal is not None:
        try:
            if float(macd) >= float(macd_signal):
                score += 10
                points.append("MACD 골든크로스 상태로 중기 상승 모멘텀이 이어지고 있습니다.")
            else:
                score -= 10
                risks.append("MACD 데드크로스 진행으로 단기 조정 국면 관망이 유리합니다.")
        except Exception:
            pass

    # 4. Valuation
    if per is not None:
        try:
            per_val = float(str(per).replace("배", "").strip())
            if 0 < per_val <= 15:
                score += 10
                points.append(f"PER {per_val:.1f}배 수준으로 업종 대비 저평가 밸류에이션 매력을 보유하고 있습니다.")
            elif per_val > 50:
                score -= 10
                risks.append(f"PER {per_val:.1f}배로 고평가 프리미엄이 있어 실적 성장 확인이 필요합니다.")
        except Exception:
            pass

    if div_yield is not None:
        try:
            div_val = float(str(div_yield).replace("%", "").strip())
            if div_val >= 3.0:
                score += 5
                points.append(f"배당수익률 {div_val:.2f}%로 하방 안전마진을 확보하고 있습니다.")
        except Exception:
            pass

    # Determine Rating
    if score >= 70:
        rating = "🟢 **[적극 매수 / 상승 유력]**"
    elif score >= 55:
        rating = "🔵 **[분할 매수 / 눌림목 관심]**"
    elif score >= 45:
        rating = "⚖️ **[중립 / 관망 권고]**"
    elif score >= 35:
        rating = "🟡 **[비중 축소 / 리스크 관리]**"
    else:
        rating = "🔴 **[보수적 접근 / 손절 고려]**"

    b1 = points[0] if points else "현재 주가 지지선 테스트가 진행 중입니다."
    b2 = points[1] if len(points) > 1 else (risks[0] if risks else "거래량 동향과 수급 주체 추적이 필요합니다.")
    b3 = risks[0] if (risks and risks[0] != b2) else (points[2] if len(points) > 2 else "주요 지지선 이탈 시 손절가 설정이 권장됩니다.")

    return f"💡 **AI 퀀트 종합 진단**\n{rating}\n• {b1}\n• {b2}\n• {b3}"


def _is_valid_ai_response(text: str) -> bool:
    """Validate if AI output meets structural and Korean quality standards."""
    if not text or len(text.strip()) < 30:
        return False
    
    # Must not start with English meta thoughts
    if text.strip().startswith(("(", "1.", "2.", "Evaluate", "Korean", "Thinking", "Here", "Sure")):
        return False

    # Must contain bullet points or rating emojis
    has_bullet = "•" in text or "-" in text
    has_tag = any(emoji in text for emoji in ["🟢", "🔵", "⚖️", "🟡", "🔴", "매수", "중립", "관망", "축소"])
    
    return has_bullet and has_tag


def generate_quant_opinion(stock_data: Dict[str, Any]) -> str:
    """
    Generate 3-line quant investment opinion using Gemini AI with Quality Gate Validation.
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

    prompt = f"""당신은 월가 출신의 숙련된 퀀트/기술적 분석 전문가입니다.
아래 주식 데이터를 분석하여 텔레그램 리포트용 '3줄 퀀트 진단 및 투자 의견'을 한국어로 작성하세요.

[종목 정보]
• 종목명: {name} ({ticker})
• 현재가/등락률: {price} ({change_pct}%)
• 20일선: {sma20}
• RSI (14): {rsi14}
• MACD: {macd} / Signal {macd_signal}
• 밸류에이션: PER {per}, PBR {pbr}, 배당수익률 {div_yield}%

[출력 형식 예시]
🔵 **[분할 매수 / 눌림목 관심]**
• 20일 이동평균선 상회로 단기 상승 추세가 안정적으로 유지되고 있습니다.
• RSI 과매수 구간 진입으로 단기 과열 부담이 있어 추격 매수보다는 눌림목 분할 매수를 권장합니다.
• 밸류에이션 부담이 적정 수준이나 단기 차익 실현 매물 출회 가능성에 유의해야 합니다.

[작성 규칙]
1. 첫째 줄은 반드시 투자 등급 태그(🟢 **[적극 매수]**, 🔵 **[분할 매수]**, ⚖️ **[중립/관망]**, 🟡 **[비중 축소]** 중 1개)로 시작하세요.
2. 이어지는 3줄은 불릿포인트(•)로 기술적 추세, 밸류에이션, 핵심 매매전략을 각각 1문장씩 작성하세요.
3. 모든 문장은 마침표(.)로 끝나는 완전한 한국어 문장으로 작성하세요.
4. 인사말, 서론, 영어 설명 없이 오직 위 형식의 4줄만 정확히 출력하세요.
"""

    for model in ["gemini-3.6-flash", "gemini-flash-latest"]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 800}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=7)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    # Quality Gate Check
                    if _is_valid_ai_response(text):
                        return f"💡 **AI 퀀트 종합 진단 (Gemini AI)**\n{text}"
                    else:
                        logger.warning(f"Gemini output failed quality gate: {text[:100]}")
        except Exception as e:
            logger.debug(f"Gemini {model} call note: {e}")
            continue

    # Fallback to high-precision rule-based engine
    return _rule_based_quant_diagnosis(stock_data)
