from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base

if TYPE_CHECKING:
    from benlab_api.models.member import Member


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    receiver_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)

    sender: Mapped["Member"] = relationship(
        "Member",
        foreign_keys=[sender_id],
        back_populates="sent_messages",
    )
    receiver: Mapped["Member"] = relationship(
        "Member",
        foreign_keys=[receiver_id],
        back_populates="received_messages",
    )
