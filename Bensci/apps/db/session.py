from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from apps.core.config import settings

_ALLOWED_JOURNAL_MODES = {"DELETE", "TRUNCATE", "PERSIST", "MEMORY", "WAL", "OFF"}
_ALLOWED_SYNCHRONOUS = {"OFF", "NORMAL", "FULL", "EXTRA", "0", "1", "2", "3"}


def _safe_journal_mode(value: str) -> str:
    mode = str(value or "WAL").strip().upper()
    return mode if mode in _ALLOWED_JOURNAL_MODES else "WAL"


def _safe_synchronous(value: str) -> str:
    mode = str(value or "NORMAL").strip().upper()
    return mode if mode in _ALLOWED_SYNCHRONOUS else "NORMAL"


_CONNECT_TIMEOUT_SECONDS = max(1.0, float(settings.sqlite_busy_timeout_seconds))
_BUSY_TIMEOUT_MS = int(max(1000, _CONNECT_TIMEOUT_SECONDS * 1000))

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False, "timeout": _CONNECT_TIMEOUT_SECONDS},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False, class_=Session)


@event.listens_for(engine, "connect")
def _apply_sqlite_pragmas(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"PRAGMA journal_mode={_safe_journal_mode(settings.sqlite_journal_mode)}")
        cursor.execute(f"PRAGMA busy_timeout={_BUSY_TIMEOUT_MS}")
        cursor.execute(f"PRAGMA synchronous={_safe_synchronous(settings.sqlite_synchronous)}")
    finally:
        cursor.close()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
