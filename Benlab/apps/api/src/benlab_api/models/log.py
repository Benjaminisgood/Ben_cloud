from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base

if TYPE_CHECKING:
    from benlab_api.models.event import Event
    from benlab_api.models.item import Item
    from benlab_api.models.location import Location
    from benlab_api.models.member import Member


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Log(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("members.id", ondelete="SET NULL"), index=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="SET NULL"), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="SET NULL"), index=True)
    action_type: Mapped[str] = mapped_column(String(50), default="")
    details: Mapped[str] = mapped_column(Text, default="")

    user: Mapped["Member | None"] = relationship(back_populates="logs")
    item: Mapped["Item | None"] = relationship(back_populates="logs")
    location: Mapped["Location | None"] = relationship(back_populates="logs")
    event: Mapped["Event | None"] = relationship(back_populates="logs")
