from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from .common import TimestampMixin


class Comment(Base, TimestampMixin):
    __tablename__ = "comment"

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey("record.id"), nullable=False, index=True)
    record = relationship("Record", backref="comments", lazy="joined")
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user = relationship("User", backref="comments", lazy="joined")
    body = Column(Text, nullable=False)


Index("ix_comment_record_created", Comment.record_id, Comment.created_at)

