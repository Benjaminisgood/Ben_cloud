from __future__ import annotations

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from ..db.base import Base
from .common import TimestampMixin


class Booking(Base, TimestampMixin):
    __tablename__ = "booking"
    __table_args__ = (
        CheckConstraint("check_out_date > check_in_date", name="ck_booking_checkout_after_checkin"),
    )

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    customer_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)

    check_in_date = Column(Date, nullable=False, index=True)
    check_out_date = Column(Date, nullable=False, index=True)
    total_nights = Column(Integer, nullable=False)

    guest_count = Column(Integer, nullable=False)
    guest_name = Column(String(80), nullable=False)
    guest_phone = Column(String(40), nullable=False)
    note = Column(Text, nullable=False, default="")

    status = Column(String(32), nullable=False, index=True, default="pending_review")
    payment_received = Column(Boolean, nullable=False, default=False)
    payment_confirmed_at = Column(DateTime, nullable=True)

    review_note = Column(Text, nullable=False, default="")
    reviewed_by_admin_id = Column(Integer, ForeignKey("user.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
