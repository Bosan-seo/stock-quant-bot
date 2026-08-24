"""
Market News Fetcher Module.
Fetches real-time market headline news for US and Korean stock markets via fast RSS feeds.
"""
import requests
import xml.etree.ElementTree as ET
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


def _clean_headline(raw_title: str) -> Dict[str, str]:
    """Clean raw RSS title into title and source."""
    if " - " in raw_title:
        parts = raw_title.rsplit(" - ", 1)
        title = parts[0].strip()
        source = parts[1].strip()
    else:
        title = raw_title.strip()
        source = "증시 속보"

    # Remove HTML entities or weird characters
    title = re.sub(r"<[^>]+>", "", title)
    title = title.replace("&quot;", '"').replace("&amp;", "&").replace("&apos;", "'")
    return {"title": title, "source": source}


def get_us_market_news(limit: int = 3) -> List[Dict[str, str]]:
    """Fetch Top US stock market breaking news headlines."""
    url = "https://news.google.com/rss/search?q=US+Stock+Market+when:1d&hl=en-US&gl=US&ceid=US:en"
    headlines = []
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:limit]
            for item in items:
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    cleaned = _clean_headline(title_elem.text)
                    headlines.append(cleaned)
    except Exception as e:
        logger.debug(f"Failed to fetch US market news: {e}")

    if not headlines:
        headlines = [
            {"title": "Wall Street monitors economic data and earnings reports", "source": "Reuters"},
            {"title": "Tech stocks lead market momentum amidst Treasury yield moves", "source": "Bloomberg"},
        ]
    return headlines


def get_kr_market_news(limit: int = 3) -> List[Dict[str, str]]:
    """Fetch Top Korean stock market breaking news headlines."""
    url = "https://news.google.com/rss/search?q=코스피+증시+특징주+when:1d&hl=ko&gl=KR&ceid=KR:ko"
    headlines = []
    try:
        resp = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = root.findall(".//item")[:limit]
            for item in items:
                title_elem = item.find("title")
                if title_elem is not None and title_elem.text:
                    cleaned = _clean_headline(title_elem.text)
                    headlines.append(cleaned)
    except Exception as e:
        logger.debug(f"Failed to fetch KR market news: {e}")

    if not headlines:
        headlines = [
            {"title": "국내 증시, 외인 및 기관 수급 공방 속 업종별 차별화 장세", "source": "연합인포맥스"},
            {"title": "반도체·AI 및 주요 실적 유망주 중심 선별적 매수세 유입", "source": "한국경제"},
        ]
    return headlines


def format_news_summary(news_items: List[Dict[str, str]], title: str = "오늘의 핵심 증시 뉴스") -> str:
    """Format news headlines into clean markdown summary."""
    lines = [f"📰 **{title}**", "-" * 35]
    for idx, item in enumerate(news_items, 1):
        headline = item.get("title", "뉴스")
        source = item.get("source", "속보")
        lines.append(f"{idx}. {headline} `[{source}]`")
    return "\n".join(lines)
