from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import Booking, Property, User


def count_properties(db: Session, *, active_only: bool = False) -> int:
    stmt = select(func.count()).select_from(Property)
    if active_only:
        stmt = stmt.where(Property.is_active.is_(True))
    return int(db.scalar(stmt) or 0)


def count_users(db: Session) -> int:
    stmt = select(func.count()).select_from(User)
    return int(db.scalar(stmt) or 0)


def count_active_users_since(db: Session, *, since: datetime) -> int:
    stmt = select(func.count(func.distinct(Booking.customer_id))).where(
        Booking.customer_id.is_not(None),
        Booking.created_at >= since,
    )
    return int(db.scalar(stmt) or 0)


def count_bookings(db: Session) -> int:
    stmt = select(func.count()).select_from(Booking)
    return int(db.scalar(stmt) or 0)


def count_bookings_by_status(db: Session, *, status: str, since: datetime | None = None) -> int:
    stmt = select(func.count()).select_from(Booking).where(Booking.status == status)
    if since is not None:
        stmt = stmt.where(Booking.created_at >= since)
    return int(db.scalar(stmt) or 0)


def count_bookings_since(db: Session, *, since: datetime) -> int:
    stmt = select(func.count()).select_from(Booking).where(Booking.created_at >= since)
    return int(db.scalar(stmt) or 0)


def sum_confirmed_revenue(db: Session, *, since: datetime | None = None, unit_price: int = 100) -> int:
    stmt = select(func.sum(Booking.total_nights * unit_price)).where(Booking.status == "confirmed")
    if since is not None:
        stmt = stmt.where(Booking.created_at >= since)
    return int(db.scalar(stmt) or 0)


def avg_confirmed_order_value(db: Session, *, since: datetime | None = None, unit_price: int = 100) -> float:
    stmt = select(func.avg(Booking.total_nights * unit_price)).where(Booking.status == "confirmed")
    if since is not None:
        stmt = stmt.where(Booking.created_at >= since)
    return float(db.scalar(stmt) or 0.0)


def list_city_property_counts(db: Session) -> list[tuple[str, int]]:
    rows = db.execute(
        select(Property.city, func.count().label("count"))
        .group_by(Property.city)
        .order_by(func.count().desc())
    ).all()
    return [(city or "", int(count or 0)) for city, count in rows]


def get_active_property_price_stats(db: Session) -> tuple[int, int, float]:
    row = db.execute(
        select(
            func.min(Property.price_per_night).label("min_price"),
            func.max(Property.price_per_night).label("max_price"),
            func.avg(Property.price_per_night).label("avg_price"),
        )
        .select_from(Property)
        .where(Property.is_active.is_(True))
    ).first()
    if not row:
        return 0, 0, 0.0
    return int(row.min_price or 0), int(row.max_price or 0), float(row.avg_price or 0.0)


def list_daily_booking_trend(db: Session, *, since: datetime) -> list[tuple[str, int]]:
    rows = db.execute(
        select(
            func.date(Booking.created_at).label("day"),
            func.count().label("count"),
        )
        .where(Booking.created_at >= since)
        .group_by(func.date(Booking.created_at))
        .order_by(func.date(Booking.created_at))
    ).all()
    return [(str(day), int(count or 0)) for day, count in rows]


def list_booking_status_distribution(db: Session, *, since: datetime) -> list[tuple[str, int]]:
    rows = db.execute(
        select(Booking.status, func.count().label("count"))
        .where(Booking.created_at >= since)
        .group_by(Booking.status)
    ).all()
    return [(str(status), int(count or 0)) for status, count in rows]


def list_popular_properties(db: Session, *, since: datetime, limit: int = 10) -> list[tuple[int, str, int]]:
    rows = db.execute(
        select(
            Property.id,
            Property.title,
            func.count(Booking.id).label("booking_count"),
        )
        .join(Booking, Property.id == Booking.property_id)
        .where(Booking.created_at >= since)
        .group_by(Property.id, Property.title)
        .order_by(func.count(Booking.id).desc())
        .limit(limit)
    ).all()
    return [(int(pid), str(title), int(count or 0)) for pid, title, count in rows]


def list_monthly_revenue(db: Session, *, since: datetime, unit_price: int = 100) -> list[tuple[str, int]]:
    rows = db.execute(
        select(
            func.strftime("%Y-%m", Booking.created_at).label("month"),
            func.sum(Booking.total_nights * unit_price).label("revenue"),
        )
        .where(Booking.status == "confirmed", Booking.created_at >= since)
        .group_by(func.strftime("%Y-%m", Booking.created_at))
        .order_by(func.strftime("%Y-%m", Booking.created_at))
    ).all()
    return [(str(month), int(revenue or 0)) for month, revenue in rows]
