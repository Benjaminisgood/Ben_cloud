from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class HealthRecord(Base):
    __tablename__ = "health_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    domain: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(160))
    summary: Mapped[str] = mapped_column(Text)
    care_status: Mapped[str] = mapped_column(String(24), default="active", index=True)
    concern_level: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="approved", index=True)
    started_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    frequency: Mapped[str] = mapped_column(String(24), default="once")
    metric_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    metric_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    metric_unit: Mapped[str | None] = mapped_column(String(24), nullable=True)
    mood_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    energy_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pain_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sleep_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    food_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    exercise_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    provider_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    medication_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    follow_up_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
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
