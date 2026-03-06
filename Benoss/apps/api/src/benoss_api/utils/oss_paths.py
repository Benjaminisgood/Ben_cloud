from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from ..core.config import get_settings


def _safe_suffix(filename: str) -> str:
    suffix = Path(filename or "").suffix.lower()
    if not suffix or len(suffix) > 16:
        return ""
    if not all(ch.isalnum() or ch == "." for ch in suffix):
        return ""
    return suffix


def record_content_key(content_uuid: str, filename: str = "", when: datetime | None = None) -> str:
    now = when or datetime.now(UTC).replace(tzinfo=None)
    prefix = get_settings().OSS_PREFIX
    suffix = _safe_suffix(filename)
    day = now.strftime("%Y-%m-%d")
    return f"{prefix}/records/{day}/objects/{content_uuid}{suffix}"


def generated_asset_key(
    user_id: int,
    asset_kind: str,
    asset_uuid: str,
    filename: str = "",
    when: datetime | None = None,
) -> str:
    now = when or datetime.now(UTC).replace(tzinfo=None)
    prefix = get_settings().OSS_PREFIX
    day = now.strftime("%Y-%m-%d")
    suffix = _safe_suffix(filename)
    safe_kind = (asset_kind or "asset").strip().replace("/", "-")
    return f"{prefix}/generated/{day}/user-{int(user_id)}/{safe_kind}/{asset_uuid}{suffix}"
