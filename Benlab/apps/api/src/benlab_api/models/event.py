from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, backref, mapped_column, relationship

from benlab_api.db.base import Base
from benlab_api.models.association import event_items, event_locations

if TYPE_CHECKING:
    from benlab_api.models.attachment import Attachment
    from benlab_api.models.item import Item
    from benlab_api.models.location import Location
    from benlab_api.models.log import Log
    from benlab_api.models.member import Member


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class EventParticipant(Base):
    __tablename__ = "event_participants"

    event_id: Mapped[int] = mapped_column(ForeignKey("events.id", ondelete="CASCADE"), primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20), default="participant", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="confirmed", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)

    event: Mapped["Event"] = relationship(back_populates="participant_links")
    member: Mapped["Member"] = relationship(back_populates="event_participations")


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    visibility: Mapped[str] = mapped_column(String(20), default="personal", nullable=False)
    owner_id: Mapped[int] = mapped_column(ForeignKey("members.id", ondelete="CASCADE"), nullable=False, index=True)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    detail_link: Mapped[str] = mapped_column(String(255), default="")
    feedback_log: Mapped[str] = mapped_column(Text, default="")
    allow_participant_edit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=_utcnow_naive,
        onupdate=_utcnow_naive,
        nullable=False,
    )

    owner: Mapped["Member"] = relationship(backref=backref("events_owned", lazy="dynamic"))
    participant_links: Mapped[list[EventParticipant]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    participants: Mapped[list["Member"]] = relationship(
        "Member",
        secondary="event_participants",
        viewonly=True,
        lazy="selectin",
    )

    items: Mapped[list["Item"]] = relationship(
        secondary=event_items,
        back_populates="events",
        lazy="selectin",
    )
    locations: Mapped[list["Location"]] = relationship(
        secondary=event_locations,
        back_populates="events",
        lazy="selectin",
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="event",
        cascade="all, delete-orphan",
        single_parent=True,
        lazy="selectin",
    )
    logs: Mapped[list["Log"]] = relationship(back_populates="event")

    def can_view(self, member: "Member | None") -> bool:
        if self.visibility == "public":
            return True
        if member is None:
            return False
        if member.id == self.owner_id:
            return True
        return any(link.member_id == member.id for link in self.participant_links)

    def can_edit(self, member: "Member | None") -> bool:
        if member is None:
            return False
        if member.id == self.owner_id:
            return True
        if self.visibility == "internal" and self.allow_participant_edit:
            return any(link.member_id == member.id for link in self.participant_links)
        return False

    def is_participant(self, member: "Member | None") -> bool:
        if member is None:
            return False
        return any(link.member_id == member.id for link in self.participant_links)

    def can_join(self, member: "Member | None") -> bool:
        if member is None or member.id == self.owner_id:
            return False
        if self.visibility != "public":
            return False
        return not self.is_participant(member)

    def participant_count(self) -> int:
        return len(self.participant_links or [])
