from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benjournal_api.db.base import Base


class JournalDay(Base):
    __tablename__ = "journal_days"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    stt_text: Mapped[str] = mapped_column(Text, default="")
    entry_text: Mapped[str] = mapped_column(Text, default="")
    segment_count: Mapped[int] = mapped_column(Integer, default=0)
    total_audio_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_provider: Mapped[str] = mapped_column(String(40), default="local")
    storage_status: Mapped[str] = mapped_column(String(20), default="pending")
    transcript_status: Mapped[str] = mapped_column(String(20), default="pending")
    combined_audio_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    combined_audio_object_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    combined_audio_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    last_error_message: Mapped[str] = mapped_column(Text, default="")
    last_recorded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_transcribed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[str] = mapped_column(String(80))
    updated_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    segments: Mapped[list["JournalAudioSegment"]] = relationship(
        back_populates="journal_day",
        cascade="all, delete-orphan",
        order_by="JournalAudioSegment.sequence_no",
    )
