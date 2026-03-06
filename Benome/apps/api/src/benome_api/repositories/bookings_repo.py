from __future__ import annotations

from datetime import date

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..models import Booking, BookingNightLock


def create_booking(
    db: Session,
    *,
    property_id: int,
    customer_id: int | None,
    check_in_date: date,
    check_out_date: date,
    total_nights: int,
    guest_count: int,
    guest_name: str,
    guest_phone: str,
    note: str,
) -> Booking:
    item = Booking(
        property_id=property_id,
        customer_id=customer_id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        total_nights=total_nights,
        guest_count=guest_count,
        guest_name=guest_name,
        guest_phone=guest_phone,
        note=note,
        status="pending_review",
    )
    db.add(item)
    db.flush()
    return item


def get_booking_by_id(db: Session, *, booking_id: int) -> Booking | None:
    return db.scalar(select(Booking).where(Booking.id == booking_id))


def list_customer_bookings(db: Session, *, customer_id: int) -> list[Booking]:
    stmt = select(Booking).where(Booking.customer_id == customer_id).order_by(Booking.created_at.desc(), Booking.id.desc())
    return list(db.scalars(stmt).all())


def list_pending_bookings(db: Session) -> list[Booking]:
    stmt = select(Booking).where(Booking.status == "pending_review").order_by(Booking.created_at.asc(), Booking.id.asc())
    return list(db.scalars(stmt).all())


def list_all_bookings(db: Session) -> list[Booking]:
    """获取所有预订，按创建时间倒序排列"""
    stmt = select(Booking).order_by(Booking.created_at.desc(), Booking.id.desc())
    return list(db.scalars(stmt).all())


def list_locked_dates(db: Session, *, property_id: int, start_date: date, end_date: date) -> list[date]:
    stmt = (
        select(BookingNightLock.stay_date)
        .where(
            and_(
                BookingNightLock.property_id == property_id,
                BookingNightLock.stay_date >= start_date,
                BookingNightLock.stay_date < end_date,
            )
        )
        .order_by(BookingNightLock.stay_date.asc())
    )
    return list(db.scalars(stmt).all())


def create_night_locks(db: Session, *, property_id: int, booking_id: int, stay_dates: list[date]) -> None:
    for stay_date in stay_dates:
        db.add(
            BookingNightLock(
                property_id=property_id,
                booking_id=booking_id,
                stay_date=stay_date,
            )
        )
