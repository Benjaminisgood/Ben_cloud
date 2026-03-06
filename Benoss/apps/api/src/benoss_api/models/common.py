from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime


def utcnow_naive() -> datetime:
    """Return UTC datetime without tzinfo for current DB schema compatibility."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)
    updated_at = Column(DateTime, nullable=False, default=utcnow_naive, onupdate=utcnow_naive)
