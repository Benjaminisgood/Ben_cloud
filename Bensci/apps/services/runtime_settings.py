from __future__ import annotations

from sqlalchemy import select

from apps.db.models import RuntimeSetting
from apps.db.session import SessionLocal

AUTO_ENRICHMENT_ENABLED_KEY = "auto_enrichment_enabled"


def _parse_bool_text(value: str | None, *, default: bool) -> bool:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)


def load_bool_runtime_setting(key: str, *, default: bool) -> bool:
    session = SessionLocal()
    try:
        item = session.scalar(select(RuntimeSetting).where(RuntimeSetting.key == key))
        if item is None:
            return bool(default)
        return _parse_bool_text(item.value, default=default)
    except Exception:
        return bool(default)
    finally:
        session.close()


def save_bool_runtime_setting(key: str, value: bool) -> None:
    session = SessionLocal()
    try:
        item = session.scalar(select(RuntimeSetting).where(RuntimeSetting.key == key))
        text = "1" if bool(value) else "0"
        if item is None:
            item = RuntimeSetting(key=key, value=text)
            session.add(item)
        else:
            item.value = text
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def load_auto_enrichment_enabled(*, default: bool) -> bool:
    return load_bool_runtime_setting(AUTO_ENRICHMENT_ENABLED_KEY, default=default)


def save_auto_enrichment_enabled(value: bool) -> None:
    save_bool_runtime_setting(AUTO_ENRICHMENT_ENABLED_KEY, value)
