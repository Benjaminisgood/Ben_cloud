from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from .common import TimestampMixin


class Property(Base, TimestampMixin):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    title = Column(String(120), nullable=False)
    description = Column(Text, nullable=False, default="")
    city = Column(String(80), nullable=False, default="", index=True)
    address = Column(String(255), nullable=False, default="")
    price_per_night = Column(Integer, nullable=False)
    max_guests = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, index=True)
    created_by_admin_id = Column(Integer, ForeignKey("user.id"), nullable=False)

    media = relationship("PropertyMedia", backref="property", cascade="all, delete-orphan")
