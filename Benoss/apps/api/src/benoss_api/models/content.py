from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from ..db.base import Base
from .common import TimestampMixin


class Content(Base, TimestampMixin):
    __tablename__ = "content"

    id = Column(Integer, primary_key=True)
    kind = Column(String(16), nullable=False)  # text | file
    file_type = Column(String(16), nullable=False, default="file")
    text_content = Column(Text, nullable=False, default="")
    oss_key = Column(String(512), nullable=False, default="")
    filename = Column(String(255), nullable=False, default="")
    content_type = Column(String(255), nullable=False, default="")
    size_bytes = Column(Integer, nullable=False, default=0)
    sha256 = Column(String(64), nullable=False, default="")

