from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Date, DateTime, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base
from benlab_api.models.association import event_items, item_locations, item_members
from benlab_api.services.detail_refs import parse_detail_refs, serialize_detail_refs

if TYPE_CHECKING:
    from benlab_api.models.attachment import Attachment
    from benlab_api.models.event import Event
    from benlab_api.models.location import Location
    from benlab_api.models.log import Log
    from benlab_api.models.member import Member


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    detail_refs_raw: Mapped[str] = mapped_column("detail_refs", Text, default="")
    category: Mapped[str] = mapped_column(String(50), default="")
    status: Mapped[str] = mapped_column(String(50), default="正常")
    features: Mapped[str] = mapped_column(String(200), default="")
    value: Mapped[float | None] = mapped_column(Float)
    quantity_desc: Mapped[str] = mapped_column(String(120), default="")
    purchase_date: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str] = mapped_column(Text, default="")
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)
    purchase_link: Mapped[str] = mapped_column(String(255), default="")

    responsible_members: Mapped[list["Member"]] = relationship(
        secondary=item_members,
        back_populates="items",
        lazy="selectin",
    )
    locations: Mapped[list["Location"]] = relationship(
        secondary=item_locations,
        back_populates="items",
        lazy="selectin",
    )

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="item",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )
    logs: Mapped[list["Log"]] = relationship(back_populates="item")

    events: Mapped[list["Event"]] = relationship(
        secondary=event_items,
        back_populates="items",
        lazy="selectin",
    )

    @property
    def detail_refs(self) -> list[dict[str, str]]:
        return parse_detail_refs(self.detail_refs_raw)

    @detail_refs.setter
    def detail_refs(self, value):
        self.detail_refs_raw = serialize_detail_refs(value)

    @property
    def attachment_filenames(self) -> list[str]:
        return [att.filename for att in self.attachments if att.filename]

    @property
    def primary_responsible(self):
        return self.responsible_members[0] if self.responsible_members else None
