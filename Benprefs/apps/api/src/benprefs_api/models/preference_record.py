from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class PreferenceRecord(Base):
    __tablename__ = "preference_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(32), index=True)
    subject_name: Mapped[str] = mapped_column(String(160), index=True)
    aspect: Mapped[str] = mapped_column(String(80))
    stance: Mapped[str] = mapped_column(String(24), index=True)
    timeframe: Mapped[str] = mapped_column(String(24), index=True)
    validation_state: Mapped[str] = mapped_column(String(24), default="hypothesis", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="approved", index=True)
    intensity: Mapped[int] = mapped_column(Integer, default=5)
    certainty: Mapped[int] = mapped_column(Integer, default=5)
    context: Mapped[str | None] = mapped_column(String(120), nullable=True)
    merchant_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(24), default="manual")
    trigger_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    supporting_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    valid_from: Mapped[date | None] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_by: Mapped[str] = mapped_column(String(80))
    updated_by: Mapped[str] = mapped_column(String(80))
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
