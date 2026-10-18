"""
User preference and analysis style configuration module.
Persists settings such as diagnosis style (STANDARD, CONSERVATIVE, MOMENTUM, MACRO) in a JSON file.
"""
import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

CONFIG_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "user_config.json"
)

# Supported analysis styles
STYLE_STANDARD = "STANDARD"          # ⚖️ 스탠다드 (균형잡힌 퀀트)
STYLE_CONSERVATIVE = "CONSERVATIVE"  # 🛡️ 보수적 가치/배당 (리스크 관리)
STYLE_MOMENTUM = "MOMENTUM"          # 🚀 공격적 모멘텀 (돌파/추세)
STYLE_MACRO = "MACRO"                # 🧠 매크로/스토리 (시황/수급 연계)

STYLE_NAMES = {
    STYLE_STANDARD: "⚖️ 스탠다드 (균형 퀀트)",
    STYLE_CONSERVATIVE: "🛡️ 보수적 가치/배당 (리스크 관리)",
    STYLE_MOMENTUM: "🚀 공격적 모멘텀 (돌파/추세)",
    STYLE_MACRO: "🧠 매크로/스토리 (시황·거시 연계)"
}

DEFAULT_CONFIG: Dict[str, Any] = {
    "analysis_style": STYLE_STANDARD
}


def load_user_config() -> Dict[str, Any]:
    """Load configuration from JSON file or return defaults."""
    if not os.path.exists(CONFIG_FILE_PATH):
        save_user_config(DEFAULT_CONFIG)
        return DEFAULT_CONFIG.copy()

    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return DEFAULT_CONFIG.copy()
            data.setdefault("analysis_style", STYLE_STANDARD)
            return data
    except Exception as e:
        logger.error(f"Failed to load user config: {e}")
        return DEFAULT_CONFIG.copy()


def save_user_config(config: Dict[str, Any]) -> bool:
    """Save configuration to JSON file."""
    try:
        with open(CONFIG_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save user config: {e}")
        return False


def get_current_style() -> str:
    """Return currently active analysis style code."""
    config = load_user_config()
    style = config.get("analysis_style", STYLE_STANDARD)
    if style not in STYLE_NAMES:
        return STYLE_STANDARD
    return style


def set_current_style(style: str) -> bool:
    """Update active analysis style."""
    if style not in STYLE_NAMES:
        return False
    config = load_user_config()
    config["analysis_style"] = style
    return save_user_config(config)


def get_style_name(style: str) -> str:
    """Return human-readable style name."""
    return STYLE_NAMES.get(style, STYLE_NAMES[STYLE_STANDARD])
