from __future__ import annotations

from benlab_api.core.config import get_settings
from benlab_api.models import Member


def admin_username() -> str:
    return str(get_settings().ADMIN_USERNAME or "").strip()


def is_admin_username(username: str) -> bool:
    configured = admin_username()
    return bool(configured) and str(username or "").strip() == configured


def is_admin_member(member: Member | None) -> bool:
    if member is None:
        return False
    return is_admin_username(member.username)
