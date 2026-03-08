from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benjournal_api.db.base import Base


class JournalAudioSegment(Base):
    __tablename__ = "journal_audio_segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    journal_day_id: Mapped[int] = mapped_column(
        ForeignKey("journal_days.id", ondelete="CASCADE"),
        index=True,
    )
    sequence_no: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    file_extension: Mapped[str] = mapped_column(String(20))
    mime_type: Mapped[str] = mapped_column(String(120))
    local_path: Mapped[str] = mapped_column(String(500))
    byte_size: Mapped[int] = mapped_column(Integer, default=0)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    journal_day: Mapped["JournalDay"] = relationship(back_populates="segments")
