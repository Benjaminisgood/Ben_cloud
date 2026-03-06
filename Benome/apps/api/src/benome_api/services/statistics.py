from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from ..repositories.statistics_repo import (
    avg_confirmed_order_value,
    count_active_users_since,
    count_bookings,
    count_bookings_by_status,
    count_bookings_since,
    count_properties,
    count_users,
    get_active_property_price_stats,
    list_booking_status_distribution,
    list_city_property_counts,
    list_daily_booking_trend,
    list_monthly_revenue,
    list_popular_properties,
    sum_confirmed_revenue,
)
from .errors import ServiceError

_REVENUE_UNIT_PRICE = 100


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _month_start(dt: datetime) -> datetime:
    return dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _months_ago_start(now: datetime, months: int) -> datetime:
    # Include current month: months=1 => current month start.
    year = now.year
    month = now.month - (months - 1)
    while month <= 0:
        month += 12
        year -= 1
    return datetime(year, month, 1)


def get_overview_statistics(db: Session) -> dict:
    now = _utcnow_naive()
    thirty_days_ago = now - timedelta(days=30)
    first_day_of_month = _month_start(now)

    return {
        "total_properties": count_properties(db),
        "active_properties": count_properties(db, active_only=True),
        "total_users": count_users(db),
        "active_users": count_active_users_since(db, since=thirty_days_ago),
        "total_bookings": count_bookings(db),
        "pending_bookings": count_bookings_by_status(db, status="pending_review"),
        "confirmed_bookings": count_bookings_by_status(db, status="confirmed"),
        "bookings_this_month": count_bookings_since(db, since=first_day_of_month),
        "revenue_this_month": sum_confirmed_revenue(
            db, since=first_day_of_month, unit_price=_REVENUE_UNIT_PRICE
        ),
        "total_revenue": sum_confirmed_revenue(db, unit_price=_REVENUE_UNIT_PRICE),
    }


def get_property_statistics(db: Session) -> dict:
    by_city = [{"city": city, "count": count} for city, count in list_city_property_counts(db)]
    min_price, max_price, avg_price = get_active_property_price_stats(db)
    return {
        "by_city": by_city,
        "price_range": {
            "min_price": min_price,
            "max_price": max_price,
            "avg_price": round(avg_price, 2),
        },
    }


def get_booking_statistics(db: Session, *, days: int) -> dict:
    if days <= 0 or days > 3650:
        raise ServiceError("days must be between 1 and 3650", status_code=400)

    start_date = _utcnow_naive() - timedelta(days=days)
    daily_trend = [
        {"day": day, "count": count}
        for day, count in list_daily_booking_trend(db, since=start_date)
    ]
    by_status = [
        {"status": status, "count": count}
        for status, count in list_booking_status_distribution(db, since=start_date)
    ]
    popular_properties = [
        {"property_id": property_id, "title": title, "booking_count": booking_count}
        for property_id, title, booking_count in list_popular_properties(db, since=start_date)
    ]
    return {
        "daily_trend": daily_trend,
        "by_status": by_status,
        "popular_properties": popular_properties,
    }


def get_revenue_statistics(db: Session, *, months: int) -> dict:
    if months <= 0 or months > 120:
        raise ServiceError("months must be between 1 and 120", status_code=400)

    now = _utcnow_naive()
    since = _months_ago_start(now, months)
    monthly_rows = list_monthly_revenue(
        db,
        since=since,
        unit_price=_REVENUE_UNIT_PRICE,
    )
    monthly_trend = []
    for month_key, revenue in monthly_rows:
        year_str, month_str = month_key.split("-", 1)
        monthly_trend.append(
            {
                "year": int(year_str),
                "month": int(month_str),
                "revenue": revenue,
            }
        )

    return {
        "monthly_trend": monthly_trend,
        "total_revenue": sum_confirmed_revenue(db, unit_price=_REVENUE_UNIT_PRICE),
        "avg_order_value": round(avg_confirmed_order_value(db, unit_price=_REVENUE_UNIT_PRICE), 2),
    }
