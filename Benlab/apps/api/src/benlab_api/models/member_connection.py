from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base, TimestampMixin


class MemberConnection(TimestampMixin, Base):
    __tablename__ = "member_connections"
    __table_args__ = (
        UniqueConstraint("source_member_id", "target_member_id", name="uq_member_connections_source_target"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_member_id: Mapped[int] = mapped_column(
        ForeignKey("members.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relation_type: Mapped[str] = mapped_column(String(40), default="other", nullable=False)
    closeness: Mapped[int | None] = mapped_column(Integer)
    note: Mapped[str] = mapped_column(Text, default="")

    source_member = relationship(
        "Member",
        foreign_keys=[source_member_id],
        back_populates="outbound_connections",
    )
    target_member = relationship(
        "Member",
        foreign_keys=[target_member_id],
        back_populates="inbound_connections",
    )
