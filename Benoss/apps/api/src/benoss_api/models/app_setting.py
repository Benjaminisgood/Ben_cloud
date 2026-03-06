from __future__ import annotations

from sqlalchemy import Column, Integer, String, Text

from ..db.base import Base
from .common import TimestampMixin


class AppSetting(Base, TimestampMixin):
    __tablename__ = "app_setting"

    id = Column(Integer, primary_key=True)
    key = Column(String(128), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False, default="")

