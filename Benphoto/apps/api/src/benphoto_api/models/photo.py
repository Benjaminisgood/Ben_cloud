
from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class Photo(Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(120), default="")
    caption: Mapped[str] = mapped_column(Text, default="")
    oss_path: Mapped[str] = mapped_column(String(1024), unique=True)
    added_by: Mapped[str] = mapped_column(String(80))
    is_trashed: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    selected_for_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    tossed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
