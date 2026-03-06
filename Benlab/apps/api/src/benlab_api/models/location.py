from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base
from benlab_api.models.association import event_locations, item_locations, location_members
from benlab_api.services.detail_refs import parse_detail_refs, parse_usage_tags, serialize_detail_refs

if TYPE_CHECKING:
    from benlab_api.models.attachment import Attachment
    from benlab_api.models.event import Event
    from benlab_api.models.item import Item
    from benlab_api.models.log import Log
    from benlab_api.models.member import Member


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(20), default="正常")
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    coordinate_source: Mapped[str] = mapped_column(String(20), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    is_public: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    detail_refs_raw: Mapped[str] = mapped_column("detail_refs", Text, default="")
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)
    detail_link: Mapped[str] = mapped_column(String(255), default="")

    parent: Mapped["Location | None"] = relationship(
        "Location",
        remote_side="Location.id",
        back_populates="children",
    )
    children: Mapped[list["Location"]] = relationship(
        "Location",
        back_populates="parent",
        cascade="all, delete-orphan",
    )

    responsible_members: Mapped[list["Member"]] = relationship(
        secondary=location_members,
        back_populates="responsible_locations",
        lazy="selectin",
    )
    items: Mapped[list["Item"]] = relationship(
        secondary=item_locations,
        back_populates="locations",
        lazy="selectin",
    )

    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="location",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )
    logs: Mapped[list["Log"]] = relationship(back_populates="location")
    events: Mapped[list["Event"]] = relationship(
        secondary=event_locations,
        back_populates="locations",
        lazy="selectin",
    )

    @property
    def detail_refs(self) -> list[dict[str, str]]:
        return parse_detail_refs(self.detail_refs_raw)

    @detail_refs.setter
    def detail_refs(self, value):
        self.detail_refs_raw = serialize_detail_refs(value)

    @property
    def usage_tags(self) -> list[str]:
        return parse_usage_tags(self.detail_refs_raw)

    @property
    def detail_refs_without_usage_tags(self) -> list[dict[str, str]]:
        return [entry for entry in self.detail_refs if (entry.get("label") or "").strip().lower() != "usage_tags"]

    @property
    def attachment_filenames(self) -> list[str]:
        return [att.filename for att in self.attachments if att.filename]
