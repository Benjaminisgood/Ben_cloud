from __future__ import annotations

import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from ..core.config import get_settings

DEFAULT_ADMIN_SETTINGS: dict[str, Any] = {
    "platform_name": "ling居家",
    "currency": "CNY",
    "max_advance_days": 90,
    "min_nights": 1,
    "check_in_time": "14:00",
    "check_out_time": "12:00",
    "email_notifications": "enabled",
    "sms_notifications": "enabled",
}


def _settings_file_path() -> Path:
    settings = get_settings()
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    return settings.DATA_DIR / "admin_settings.json"


def load_admin_settings() -> dict[str, Any]:
    settings_path = _settings_file_path()
    if not settings_path.exists():
        return dict(DEFAULT_ADMIN_SETTINGS)

    try:
        raw = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return dict(DEFAULT_ADMIN_SETTINGS)

    if not isinstance(raw, dict):
        return dict(DEFAULT_ADMIN_SETTINGS)

    merged = dict(DEFAULT_ADMIN_SETTINGS)
    merged.update(raw)
    return merged


def save_admin_settings(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(DEFAULT_ADMIN_SETTINGS)
    normalized.update(payload)

    settings_path = _settings_file_path()
    settings_path.write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return normalized


def get_system_info() -> dict[str, str]:
    settings = get_settings()
    return {
        "version": settings.APP_VERSION,
        "python_version": platform.python_version(),
        "database": settings.DATABASE_URL,
        "server_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
