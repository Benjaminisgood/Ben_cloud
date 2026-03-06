from __future__ import annotations

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from ..models import User
from ..utils.runtime_settings import get_setting_str


def login_page_context(next_url: str) -> dict:
    return {"page": "login", "title": "Login", "next_url": next_url}


def register_page_context() -> dict:
    return {"page": "register", "title": "Register"}


def home_page_context(user: User) -> dict:
    return {"page": "home", "title": "Benoss Home", "current_user": user}


def board_page_context(user: User) -> dict:
    tz_name = get_setting_str("DIGEST_TIMEZONE", default="Asia/Shanghai").strip() or "Asia/Shanghai"
    try:
        tz = ZoneInfo(tz_name)
        digest_timezone = tz_name
    except Exception:
        tz = timezone.utc
        digest_timezone = "UTC"
    board_digest_day = (datetime.now(tz).date() - timedelta(days=1)).isoformat()
    return {
        "page": "board",
        "title": "Board",
        "current_user": user,
        "board_digest_day": board_digest_day,
        "digest_timezone": digest_timezone,
    }


def echoes_page_context(user: User) -> dict:
    return {"page": "echoes", "title": "Echoes", "current_user": user}


def notice_page_context(user: User) -> dict:
    return {"page": "notice", "title": "Notice", "current_user": user}


def admin_page_context(user: User) -> dict:
    return {"page": "admin", "title": "Admin", "current_user": user}


def can_access_admin(user: User) -> bool:
    return user.role == "admin"
