from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base
from benlab_api.models.association import item_members, location_members, member_follows

if TYPE_CHECKING:
    from benlab_api.models.event import EventParticipant
    from benlab_api.models.item import Item
    from benlab_api.models.location import Location
    from benlab_api.models.member_connection import MemberConnection
    from benlab_api.models.log import Log
    from benlab_api.models.message import Message


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Member(Base):
    __tablename__ = "members"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    username: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    contact: Mapped[str] = mapped_column(String(100), default="")
    photo: Mapped[str] = mapped_column(String(255), default="")
    notes: Mapped[str] = mapped_column(Text, default="")
    feedback_log: Mapped[str] = mapped_column(Text, default="")
    last_modified: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)

    items: Mapped[list["Item"]] = relationship(
        secondary=item_members,
        back_populates="responsible_members",
        lazy="selectin",
    )
    responsible_locations: Mapped[list["Location"]] = relationship(
        secondary=location_members,
        back_populates="responsible_members",
        lazy="selectin",
    )

    sent_messages: Mapped[list["Message"]] = relationship(
        back_populates="sender",
        foreign_keys="Message.sender_id",
        cascade="all, delete-orphan",
    )
    received_messages: Mapped[list["Message"]] = relationship(
        back_populates="receiver",
        foreign_keys="Message.receiver_id",
        cascade="all, delete-orphan",
    )
    logs: Mapped[list["Log"]] = relationship(back_populates="user")

    event_participations: Mapped[list["EventParticipant"]] = relationship(
        back_populates="member",
        cascade="all, delete-orphan",
    )

    following: Mapped[list["Member"]] = relationship(
        secondary=member_follows,
        primaryjoin=id == member_follows.c.follower_id,
        secondaryjoin=id == member_follows.c.followed_id,
        back_populates="followers",
        lazy="selectin",
    )
    followers: Mapped[list["Member"]] = relationship(
        secondary=member_follows,
        primaryjoin=id == member_follows.c.followed_id,
        secondaryjoin=id == member_follows.c.follower_id,
        back_populates="following",
        lazy="selectin",
    )
    outbound_connections: Mapped[list["MemberConnection"]] = relationship(
        "MemberConnection",
        foreign_keys="MemberConnection.source_member_id",
        back_populates="source_member",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    inbound_connections: Mapped[list["MemberConnection"]] = relationship(
        "MemberConnection",
        foreign_keys="MemberConnection.target_member_id",
        back_populates="target_member",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def set_password(self, raw_password: str) -> None:
        from benlab_api.services.security import hash_password

        self.password_hash = hash_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        from benlab_api.services.security import verify_password

        return verify_password(raw_password, self.password_hash)
