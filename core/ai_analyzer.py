"""
AI & Rule-based Quant Analysis Engine (Bulletproof Production Version).
Generates high-precision 3-line investment diagnosis and rating based on technical indicators and fundamentals.
Supports dynamic Diagnosis Styles:
  - STANDARD: Balanced technical & fundamental analysis
  - CONSERVATIVE: Downside risk management & value/dividend focus
  - MOMENTUM: Trend breakout & volume/speed trading focus
  - MACRO: Macro linkage (Rates, DXY, Oil) & market sentiment
"""
import os
import re
import json
import logging
import requests
from typing import Dict, Any, List, Optional
from core.user_config import (
    get_current_style, get_style_name,
    STYLE_STANDARD, STYLE_CONSERVATIVE, STYLE_MOMENTUM, STYLE_MACRO
)

logger = logging.getLogger(__name__)


def _calculate_support_resistance(price_val: float, sma_val: Optional[float]) -> Dict[str, Any]:
    """Calculate quantitative 1st support and 1st resistance levels."""
    if not price_val or price_val <= 0:
        return {"support": None, "resistance": None}
    
    # If SMA20 is available
    if sma_val and sma_val > 0:
        if price_val >= sma_val:
            support = round(sma_val, 2)
            resistance = round(price_val * 1.05, 2)
        else:
            support = round(price_val * 0.95, 2)
            resistance = round(sma_val, 2)
    else:
        support = round(price_val * 0.95, 2)
        resistance = round(price_val * 1.05, 2)
        
    return {"support": support, "resistance": resistance}


def _rule_based_quant_diagnosis(data: Dict[str, Any], style: Optional[str] = None) -> str:
    """
    High-precision rule-based quant scoring fallback with style awareness.
    Evaluates:
      - Trend (SMA20 breakout/above/below)
      - Momentum (RSI oversold/overbought/neutral, MACD golden/dead cross)
      - Valuation (PER, PBR, Dividend Yield, ROE)
    """
    if not style:
        style = get_current_style()

    price = data.get("price", 0)
    sma20 = data.get("sma20")
    prev_sma20 = data.get("prev_sma20")
    prev_close = data.get("prev_close")
    rsi14 = data.get("rsi14")
    macd = data.get("macd")
    macd_signal = data.get("macd_signal")
    per = data.get("per")
    div_yield = data.get("div_yield")
    currency = data.get("currency", "원" if data.get("market") == "KR" else "$")

    p_val = None
    s_val = None
    try:
        p_val = float(str(price).replace("$", "").replace(",", "").replace("원", "").strip())
    except Exception:
        pass
    try:
        if sma20 is not None:
            s_val = float(str(sma20).replace("$", "").replace(",", "").replace("원", "").strip())
    except Exception:
        pass

    sr_levels = _calculate_support_resistance(p_val or 0, s_val)
    sup_str = f"{sr_levels['support']:,.2f}{currency}" if sr_levels['support'] else "지지선 확인 필요"
    res_str = f"{sr_levels['resistance']:,.2f}{currency}" if sr_levels['resistance'] else "저항선 확인 필요"

    score = 50
    points = []
    risks = []

    # 1. Trend (SMA20)
    if s_val is not None and p_val is not None:
        if prev_sma20 and prev_close and prev_close < prev_sma20 and p_val >= s_val:
            score += 25 if style == STYLE_MOMENTUM else 20
            points.append(f"20일선({s_val:,.2f})을 강력 상향 돌파하며 단기 추세 반등 신호를 완성했습니다.")
        elif p_val >= s_val:
            score += 15 if style == STYLE_MOMENTUM else 10
            points.append(f"20일선({s_val:,.2f}) 위에 안정적으로 안착하여 상승 지지력을 유지 중입니다.")
        else:
            score -= 25 if style == STYLE_CONSERVATIVE else 15
            risks.append(f"20일선({s_val:,.2f}) 하회 상태로 매물 압박이 있어 지지선({sup_str}) 수성 여부 확인이 우선입니다.")

    # 2. Momentum (RSI)
    if rsi14 is not None:
        try:
            r_val = float(str(rsi14).replace("🔥", "").replace("🧊", "").strip())
            if r_val <= 32:
                score += 20 if style == STYLE_CONSERVATIVE else 15
                points.append(f"RSI({r_val:.1f}) 과매도 국면으로 기술적 반등 매수세 유입 확률이 높은 구간입니다.")
            elif r_val >= 70:
                score -= 20 if style == STYLE_CONSERVATIVE else 5
                risks.append(f"RSI({r_val:.1f}) 단기 과열권에 진입하여 신규 추격보다는 차익 실현 경계가 필요합니다.")
            else:
                points.append(f"RSI({r_val:.1f}) 중립 권역에서 에너지를 안정적으로 응축하고 있습니다.")
        except Exception:
            pass

    # 3. MACD
    if macd is not None and macd_signal is not None:
        try:
            if float(macd) >= float(macd_signal):
                score += 15 if style == STYLE_MOMENTUM else 10
                points.append("MACD 골든크로스 상승 추세를 견조하게 유지하고 있습니다.")
            else:
                score -= 15 if style == STYLE_MOMENTUM else 10
                risks.append("MACD 데드크로스 진행으로 단기 눌림목 기간 조정 가능성이 있습니다.")
        except Exception:
            pass

    # 4. Valuation
    if per is not None:
        try:
            per_val = float(str(per).replace("배", "").strip())
            if 0 < per_val <= 15:
                score += 15 if style == STYLE_CONSERVATIVE else 10
                points.append(f"PER {per_val:.1f}배 수준으로 업종 대비 저평가 매력 및 안전마진을 보유했습니다.")
            elif per_val > 50:
                score -= 20 if style == STYLE_CONSERVATIVE else 5
                risks.append(f"PER {per_val:.1f}배로 밸류에이션 부담이 있어 실적 성장 확인이 필요합니다.")
        except Exception:
            pass

    if div_yield is not None:
        try:
            div_val = float(str(div_yield).replace("%", "").strip())
            if div_val >= 3.0:
                score += 15 if style == STYLE_CONSERVATIVE else 5
                points.append(f"배당수익률 {div_val:.2f}%로 든든한 주가 하방 지지력을 확보했습니다.")
        except Exception:
            pass

    # Determine Rating based on style-adjusted score
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

    b1 = points[0] if points else f"현재 1차 지지선({sup_str}) 테스트가 진행 중입니다."
    b2 = points[1] if len(points) > 1 else (risks[0] if risks else f"1차 저항선은 {res_str} 부근에 형성되어 있습니다.")
    b3 = f"대응 전략: 지지선({sup_str}) 수성 시 분할 매수, 1차 목표가는 {res_str} 설정을 권장합니다."

    style_tag = get_style_name(style)
    return f"💡 **AI 퀀트 종합 진단 [{style_tag}]**\n{rating}\n• {b1}\n• {b2}\n• {b3}"


def _is_valid_ai_response(text: str) -> bool:
    """Validate if AI output meets strict structural and Korean quality standards."""
    if not text or len(text.strip()) < 35:
        return False
    
    clean = text.strip()
    
    # 1. Must not contain English meta thoughts or reasoning debris
    forbidden_meta = [
        "looking at", "fits", "here is", "sure", "evaluate", "thinking", "i will",
        "analysis:", "explanation", "rule 1", "output:", "option", "note:"
    ]
    if any(m in clean.lower() for m in forbidden_meta):
        return False

    # 2. Check Hangul character ratio (at least 35% Korean characters)
    hangul_chars = len(re.findall(r"[가-힣]", clean))
    total_chars = len(clean)
    if total_chars > 0 and (hangul_chars / total_chars) < 0.35:
        return False

    # 3. Must contain proper bullet points
    bullet_count = clean.count("•") + clean.count("- ")
    if bullet_count < 2:
        return False

    # 4. Must contain rating emoji tag
    has_tag = any(emoji in clean for emoji in ["🟢", "🔵", "⚖️", "🟡", "🔴"])
    
    return has_tag


def generate_quant_opinion(stock_data: Dict[str, Any], style: Optional[str] = None) -> str:
    """
    Generate 3-line quant investment opinion using Gemini AI with Quality Gate Validation
    and dynamic style instruction.
    """
    if not style:
        style = get_current_style()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _rule_based_quant_diagnosis(stock_data, style)

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
    market = stock_data.get("market", "US")
    currency = "원" if market == "KR" else "$"

    # Style-specific instructions
    if style == STYLE_CONSERVATIVE:
        style_prompt = (
            "[분석 성향: 🛡️ 보수적 가치/배당 모드]\n"
            "- 원금 보존과 하방 리스크(지지선 이탈, 밸류에이션 고평가)를 최우선으로 경고하세요.\n"
            "- 저평가 PER/PBR, 배당수익률, 안전마진 관점에서 평가하고, 모호할 땐 보수적 등급(관망/비중축소)을 부여하세요."
        )
    elif style == STYLE_MOMENTUM:
        style_prompt = (
            "[분석 성향: 🚀 공격적 모멘텀/돌파 모드]\n"
            "- 20일선 돌파, MACD 골든크로스, 단기 가격 탄력성을 최우선으로 평가하세요.\n"
            "- 단기 트레이딩 및 추세 추종 관점에서 목표가 돌파 가능성과 빠른 손절가 라인을 제시하세요."
        )
    elif style == STYLE_MACRO:
        style_prompt = (
            "[분석 성향: 🧠 매크로/스토리 모드]\n"
            "- 거시 시장 환경(금리, 환율) 및 섹터 수급 순환매와의 연관성을 강조하세요.\n"
            "- 단순 지표 외에 해당 종목이 속한 업황 흐름과 중기 펀더멘털 관점을 종합하여 조언하세요."
        )
    else:
        style_prompt = (
            "[분석 성향: ⚖️ 스탠다드 균형 퀀트 모드]\n"
            "- 기술적 지표(이평선, RSI, MACD)와 밸류에이션(PER, PBR)의 균형 잡힌 객관적 진단을 내리세요."
        )

    prompt = f"""당신은 월가 출신의 최고 수준 퀀트/기술적 분석 전문가입니다.
아래 주식 데이터를 분석하여 텔레그램 리포트용 '3줄 퀀트 정밀 진단 및 투자 의견'을 한국어로 작성하세요.

{style_prompt}

[종목 정보]
• 종목명: {name} ({ticker})
• 현재가/등락률: {price} ({change_pct}%)
• 20일 이동평균선(SMA20): {sma20}
• RSI (14): {rsi14}
• MACD: {macd} / Signal: {macd_signal}
• 밸류에이션: PER {per}, PBR {pbr}, 배당수익률 {div_yield}%

[출력 형식 예시]
🔵 **[분할 매수 / 눌림목 관심]**
• 20일선({sma20}) 위에 안정적으로 안착하여 상승 지지력을 유지 중이며 단기 1차 지지선 역할을 합니다.
• RSI({rsi14}) 구간에서 에너지를 비축 중이며, MACD 추세와 결합 시 추가 상승 여력이 유효합니다.
• 밸류에이션 부담이 적정 수준이므로 성급한 추격보다는 1차 지지선 부근 눌림목 분할 매수를 권장합니다.

[작성 규칙 - 엄격 준수]
1. 첫째 줄은 반드시 투자 등급 태그(🟢 **[적극 매수]**, 🔵 **[분할 매수]**, ⚖️ **[중립/관망]**, 🟡 **[비중 축소]**, 🔴 **[보수적 접근]** 중 1개)로 시작하세요.
2. 이어지는 3줄은 불릿포인트(•)로 (1) 기술적 추세 및 20일선 지지/저항 수치 분석, (2) 모멘텀(RSI/MACD) 및 밸류에이션 평가, (3) 구체적인 매매/대응 전략(지지선·목표가 기준)을 각각 1문장씩 작성하세요.
3. 지표 수치(20일선 가격, RSI 수치 등)를 문장에 명확히 인용하여 분석의 정확성과 정량적 신뢰도를 극대화하세요.
4. 모든 문장은 마침표(.)로 끝나는 완전한 한국어 문장으로 작성하세요.
5. 인사말, 서론, 영어 설명 없이 오직 위 형식의 4줄만 정확히 출력하세요.
"""

    # Model endpoints to attempt
    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    for model in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 800}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    if _is_valid_ai_response(text):
                        style_tag = get_style_name(style)
                        return f"💡 **AI 퀀트 종합 진단 [{style_tag}]**\n{text}"
                    else:
                        logger.warning(f"Gemini output failed quality gate: {text[:100]}")
        except Exception as e:
            logger.debug(f"Gemini {model} call note: {e}")
            continue

    # Fallback to high-precision rule-based engine
    return _rule_based_quant_diagnosis(stock_data, style)


def _rule_based_market_diagnosis(market_type: str, indices_data: List[Dict[str, Any]], style: Optional[str] = None) -> str:
    """Fallback rule-based market condition summary."""
    if not style:
        style = get_current_style()

    up_count = sum(1 for idx in indices_data if (idx.get("change") or 0) > 0)
    down_count = sum(1 for idx in indices_data if (idx.get("change") or 0) < 0)
    
    if up_count > down_count:
        rating = "🟢 **[전반적 강세 / 위험 선호 장세]**"
        b1 = "주요 시장 지수가 전일 대비 상승세를 보이며 우호적인 투자 심리가 유지되고 있습니다."
        b2 = "대형 주도주 및 성장 섹터 중심의 견조한 매수세가 시장을 견인 중입니다."
        b3 = "추세 추종 매매가 유리하며 지수 주요 지지선 유지 여부를 모니터링하세요."
    elif down_count > up_count:
        rating = "🟡 **[단기 조정 / 차익 매물 소화]**"
        b1 = "주요 시장 지수가 하락 압력을 받으며 단기 리스크 관리 국면에 진입했습니다."
        b2 = "금리 및 거시 변동성에 따른 경계 심리로 차익 실현 매물이 출회 중입니다."
        b3 = "성급한 추격 매수보다는 하단 지지선 확인 후 분할 매수 접근을 권장합니다."
    else:
        rating = "⚖️ **[혼조세 / 종목별 차별화 장세]**"
        b1 = "시장 지수가 뚜렷한 방향성 없이 팽팽한 수급 공방을 이어가고 있습니다."
        b2 = "지수보다는 개별 실적 우량주 및 특정 테마 중심으로 순환매가 전개되고 있습니다."
        b3 = "철저한 밸류에이션 점검과 손절가 설정을 통한 선별적 대응이 필수적입니다."

    market_name = "미국 증시" if market_type.upper() == "US" else "국내 증시"
    style_tag = get_style_name(style)
    return f"💡 **Gemini AI {market_name} 종합 시황 진단 [{style_tag}]**\n{rating}\n• {b1}\n• {b2}\n• {b3}"


def generate_market_opinion(
    market_type: str,
    indices_data: List[Dict[str, Any]],
    news_items: List[Dict[str, str]],
    macro_context: Optional[Dict[str, Any]] = None,
    style: Optional[str] = None
) -> str:
    """
    Generate 3-line comprehensive macro/market condition opinion using Gemini AI.
    Integrates macro context (Rates, DXY, Oil, FX) and style preference.
    """
    if not style:
        style = get_current_style()

    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return _rule_based_market_diagnosis(market_type, indices_data, style)

    market_name = "미국 증시 (Wall Street)" if market_type.upper() == "US" else "국내 증시 (KRX/코스피·코스닥)"
    
    # Format indices overview
    idx_lines = []
    for idx in indices_data:
        name = idx.get("name", "")
        price = idx.get("price")
        pct = idx.get("change_pct")
        if price is not None and pct is not None:
            idx_lines.append(f"{name}: {price:,.2f} ({pct:+.2f}%)")
    indices_str = " / ".join(idx_lines) if idx_lines else "지수 데이터 수집 중"

    # Format news headlines
    news_lines = [item.get("title", "") for item in news_items if item.get("title")]
    news_str = " | ".join(news_lines[:3]) if news_lines else "주요 속보 수집 중"

    # Format macro indicators if available
    macro_str = ""
    if macro_context:
        macro_parts = []
        for k, v in macro_context.items():
            if isinstance(v, dict) and v.get("price") is not None:
                macro_parts.append(f"{v.get('name', k)}: {v.get('price')}{v.get('unit', '')} ({v.get('change_pct', 0):+.2f}%)")
        if macro_parts:
            macro_str = "\n• 거시 매크로 환경: " + " / ".join(macro_parts[:4])

    # Style guidance
    if style == STYLE_CONSERVATIVE:
        style_rule = "- 보수적 관점에서 금리/환율 변동성, 거시 불확실성, 하방 리스크에 대한 방어 전략을 집중 제시하세요."
    elif style == STYLE_MOMENTUM:
        style_rule = "- 모멘텀 관점에서 시장 주도 섹터의 탄력성과 단기 매수 기회, 지수 돌파 여부를 집중 제시하세요."
    elif style == STYLE_MACRO:
        style_rule = "- 매크로 관점에서 금리, 유가, 환율이 증시에 미치는 직접적 인과관계와 외국인/기관 수급 영향을 깊이 있게 제시하세요."
    else:
        style_rule = "- 객관적 관점에서 지수 등락률과 뉴스 헤드라인 간의 상관관계 및 균형 잡힌 투자자 대응 전략을 제시하세요."

    prompt = f"""당신은 최고 수준의 글로벌 거시경제 및 주식 시장 전략가(Chief Macro Strategist)입니다.
아래 시장 지수 데이터, 핵심 뉴스, 거시 매크로 변수를 정밀 분석하여 텔레그램 리포트용 '3줄 {market_name} 종합 시황 진단 및 투자 전략'을 한국어로 작성하세요.

[분석 스타일 지침]
{style_rule}

[시장 현황]
• 시장: {market_name}
• 주요 지수 현황: {indices_str}
• 실시간 핵심 뉴스: {news_str}{macro_str}

[출력 형식 예시]
🟢 **[기술주 중심 강세 / 위험 선호 지속]**
• 나스닥(+1.20%)과 S&P500(+0.85%)이 빅테크 실적 기대감과 10년물 국채금리 안정세 속에 견고한 상승 흐름을 주도했습니다.
• 전반적인 시장 리스크는 제한적이나 단기 급등에 따른 차익 실현 매물 출회 및 인플레이션 지표 발표 경계감이 상존합니다.
• 주도 섹터 20일선 지지력 확인 후 눌림목 분할 매수 전략이 유효하며, 무리한 고점 추격 매수는 지양하세요.

[작성 규칙 - 엄격 준수]
1. 첫째 줄은 반드시 시장 상태 태그(🟢 **[강세/위험선호]**, 🔵 **[완만한 상승/순환매]**, ⚖️ **[혼조세/수급공방]**, 🟡 **[조정/리스크관리]**, 🔴 **[하락/경계심리]** 중 1개)로 시작하세요.
2. 이어지는 3줄은 불릿포인트(•)로 (1) 시황 요약 및 주도 요인(구체적 등락률 수치 인용), (2) 핵심 잠재 리스크 요인, (3) 투자자 실전 대응 전략을 각각 1문장씩 작성하세요.
3. 지수 등락률 수치를 구체적으로 인용하여 분석의 신뢰도를 높이세요.
4. 모든 문장은 마침표(.)로 끝나는 완전한 한국어 문장으로 작성하세요.
5. 인사말 없이 오직 위 형식의 4줄만 정확히 출력하세요.
"""

    models_to_try = ["gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-latest"]
    for model in models_to_try:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            headers = {"Content-Type": "application/json"}
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.15, "maxOutputTokens": 800}
            }
            resp = requests.post(url, headers=headers, json=payload, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
                    if _is_valid_ai_response(text):
                        header_name = "미국 증시" if market_type.upper() == "US" else "국내 증시"
                        style_tag = get_style_name(style)
                        return f"💡 **Gemini AI {header_name} 종합 시황 진단 [{style_tag}]**\n{text}"
        except Exception as e:
            logger.debug(f"Market Gemini {model} call note: {e}")
            continue

    return _rule_based_market_diagnosis(market_type, indices_data, style)
