"""
Telegram notification module with console fallback and cross-platform encoding support.
"""
import os
import sys
import requests
import logging
from dotenv import load_dotenv
from typing import Optional

# Ensure standard output streams support UTF-8 on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Load .env variables from current directory or parent directories
load_dotenv()

logger = logging.getLogger(__name__)


def safe_print(text: str) -> None:
    """Safely print text with UTF-8 fallback for terminals with restricted encoding."""
    try:
        print(text)
    except UnicodeEncodeError:
        try:
            print(text.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8"))
        except Exception:
            print(text.encode("ascii", errors="replace").decode("ascii"))


def send_telegram_message(
    message: str,
    bot_token: Optional[str] = None,
    chat_id: Optional[str] = None,
    parse_mode: str = "Markdown"
) -> bool:
    """
    Send a message via Telegram Bot API.
    If bot_token or chat_id is missing, fallback to printing the message to the console.

    Args:
        message: The message string (supports Markdown).
        bot_token: Telegram bot token. Defaults to TELEGRAM_BOT_TOKEN from env.
        chat_id: Telegram chat ID. Defaults to TELEGRAM_CHAT_ID from env.
        parse_mode: Message formatting ('Markdown' or 'HTML').

    Returns:
        bool: True if message was successfully sent via Telegram or logged to console, False on error.
    """
    token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
    chat = chat_id or os.getenv("TELEGRAM_CHAT_ID")

    # If credentials are not set or contain placeholder values, fallback to console
    if not token or not chat or "your_telegram" in token.lower() or "your_telegram" in chat.lower():
        safe_print("\n" + "=" * 50)
        safe_print("📢 [NOTIFIER FALLBACK] TELEGRAM CREDENTIALS NOT CONFIGURED")
        safe_print("=" * 50)
        safe_print(message)
        safe_print("=" * 50 + "\n")
        return True

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat,
        "text": message,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }

    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        if data.get("ok"):
            logger.info("Telegram message sent successfully.")
            safe_print("✅ 텔레그램 메시지 발송 성공 (Telegram -> 스마트폰)")
            return True
        else:
            logger.warning(f"Telegram API response error: {data}")
    except Exception as e:
        logger.error(f"Failed to send Telegram message: {e}")

    # Fallback to console on error
    safe_print("\n" + "=" * 50)
    safe_print(f"⚠️ [NOTIFIER ERROR FALLBACK] Failed to send via Telegram ({e})")
    safe_print("=" * 50)
    safe_print(message)
    safe_print("=" * 50 + "\n")
    return False
