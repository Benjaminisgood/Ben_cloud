from __future__ import annotations

from typing import Iterable

from sqlalchemy import Column, ForeignKey, Index, Integer, String, Table, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from .common import TimestampMixin


record_tags = Table(
    "record_tags",
    Base.metadata,
    Column("record_id", Integer, ForeignKey("record.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tag.id", ondelete="CASCADE"), primary_key=True),
)


class Tag(Base, TimestampMixin):
    __tablename__ = "tag"

    id = Column(Integer, primary_key=True)
    name = Column(String(40), nullable=False)
    name_norm = Column(String(40), nullable=False, unique=True)


class Record(Base, TimestampMixin):
    __tablename__ = "record"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user = relationship("User", backref="records", lazy="joined")
    content_id = Column(Integer, ForeignKey("content.id"), nullable=False, unique=True, index=True)
    content = relationship("Content", backref="record", uselist=False, lazy="joined")
    visibility = Column(String(16), nullable=False, default="private")
    tags = relationship("Tag", secondary=record_tags, lazy="selectin", backref="records")
    preview = Column(Text, nullable=False, default="")

    def get_tags(self) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for item in self.tags or []:
            text = str(getattr(item, "name", "") or "").strip()
            if not text:
                continue
            low = text.lower()
            if low in seen:
                continue
            seen.add(low)
            out.append(text)
        return out

    def set_tags(self, tags: list[str], *, db) -> None:
        cleaned = _clean_tag_names(tags)
        if not cleaned:
            self.tags = []
            return
        normalized = [t.lower() for t in cleaned]
        existing = db.query(Tag).filter(Tag.name_norm.in_(normalized)).all()
        existing_map = {t.name_norm: t for t in existing}
        next_tags: list[Tag] = []
        for text in cleaned:
            norm = text.lower()
            tag = existing_map.get(norm)
            if tag is None:
                tag = Tag(name=text, name_norm=norm)
                db.add(tag)
                existing_map[norm] = tag
            next_tags.append(tag)
        self.tags = next_tags


def _clean_tag_names(values: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = str(item or "").strip()
        if not text:
            continue
        if len(text) > 40:
            text = text[:40]
        low = text.lower()
        if low in seen:
            continue
        seen.add(low)
        result.append(text)
        if len(result) >= 20:
            break
    return result


Index("ix_record_user_created", Record.user_id, Record.created_at)
Index("ix_record_visibility_created", Record.visibility, Record.created_at)

