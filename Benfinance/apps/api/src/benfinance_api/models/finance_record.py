from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..db.base import Base


class FinanceRecord(Base):
    __tablename__ = "finance_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    record_type: Mapped[str] = mapped_column(String(24), index=True)
    title: Mapped[str] = mapped_column(String(160))
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(80), index=True)
    flow_direction: Mapped[str] = mapped_column(String(24), default="neutral")
    planning_status: Mapped[str] = mapped_column(String(24), default="planned", index=True)
    risk_level: Mapped[str] = mapped_column(String(24), default="medium", index=True)
    review_status: Mapped[str] = mapped_column(String(24), default="approved", index=True)
    amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    currency: Mapped[str] = mapped_column(String(8), default="CNY")
    account_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    counterparty: Mapped[str | None] = mapped_column(String(120), nullable=True)
    occurred_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_review_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    recurrence_rule: Mapped[str | None] = mapped_column(String(120), nullable=True)
    follow_up_action: Mapped[str | None] = mapped_column(Text, nullable=True)
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
