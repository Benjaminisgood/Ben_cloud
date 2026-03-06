from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, UniqueConstraint

from ..db.base import Base
from .common import utcnow_naive


class BookingNightLock(Base):
    __tablename__ = "booking_night_lock"
    __table_args__ = (UniqueConstraint("property_id", "stay_date", name="uq_property_stay_date"),)

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    booking_id = Column(Integer, ForeignKey("booking.id"), nullable=False)
    stay_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=utcnow_naive)
