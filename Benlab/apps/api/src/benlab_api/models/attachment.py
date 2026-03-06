from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base

if TYPE_CHECKING:
    from benlab_api.models.event import Event
    from benlab_api.models.item import Item
    from benlab_api.models.location import Location
    from benlab_api.models.publication import Publication


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int | None] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"), index=True)
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="CASCADE"), index=True)
    event_id: Mapped[int | None] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), index=True)
    publication_id: Mapped[int | None] = mapped_column(ForeignKey("publications.id", ondelete="CASCADE"), index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "(item_id IS NOT NULL) + (location_id IS NOT NULL) + (event_id IS NOT NULL) + (publication_id IS NOT NULL) = 1",
            name="single_owner",
        ),
    )

    item: Mapped["Item | None"] = relationship(back_populates="attachments")
    location: Mapped["Location | None"] = relationship(back_populates="attachments")
    event: Mapped["Event | None"] = relationship(back_populates="attachments")
    publication: Mapped["Publication | None"] = relationship(back_populates="attachments")
