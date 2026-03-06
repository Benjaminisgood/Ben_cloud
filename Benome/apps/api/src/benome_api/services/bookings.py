from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..models import Booking, User
from ..models.common import utcnow_naive
from ..repositories.bookings_repo import (
    create_booking,
    create_night_locks,
    get_booking_by_id,
    list_all_bookings,
    list_customer_bookings,
    list_locked_dates,
    list_pending_bookings,
)
from ..repositories.properties_repo import get_property_by_id
from .errors import ServiceError


def get_booking_detail(db: Session, *, booking_id: int, customer: User | None = None) -> Booking:
    """获取预订详情。
    
    Args:
        db: 数据库会话
        booking_id: 预订 ID
        customer: 当前用户（可选，用于权限检查）
    
    Returns:
        预订对象
    
    Raises:
        ServiceError: 预订不存在或无权访问
    """
    booking = get_booking_by_id(db, booking_id=booking_id)
    if not booking:
        raise ServiceError("booking not found", status_code=404)
    
    # 权限检查：只有预订人或管理员可以查看
    if customer:
        if customer.role == "admin":
            return booking
        if customer.role == "customer" and booking.customer_id == customer.id:
            return booking
        raise ServiceError("无权访问此预订", status_code=403)
    
    # 未登录用户不能查看
    raise ServiceError("请先登录", status_code=401)


def cancel_booking_request(
    db: Session,
    *,
    booking_id: int,
    customer: User,
) -> Booking:
    """取消预订。
    
    Args:
        db: 数据库会话
        booking_id: 预订 ID
        customer: 当前用户
    
    Returns:
        更新后的预订对象
    
    Raises:
        ServiceError: 预订不存在、无权取消或状态不允许取消
    """
    if customer.role != "customer":
        raise ServiceError("只有客户账号可以取消预订", status_code=403)
    
    booking = get_booking_by_id(db, booking_id=booking_id)
    if not booking:
        raise ServiceError("booking not found", status_code=404)
    
    # 只有预订人可以取消
    if booking.customer_id != customer.id:
        raise ServiceError("无权取消此预订", status_code=403)
    
    # 只有待审核状态的预订可以取消
    if booking.status != "pending_review":
        raise ServiceError(f"当前状态（{booking.status}）不能取消预订", status_code=400)
    
    # 更新预订状态
    booking.status = "cancelled"
    booking.reviewed_by_admin_id = None
    booking.review_note = "用户主动取消"
    booking.reviewed_at = utcnow_naive()
    
    db.commit()
    db.refresh(booking)
    return booking


def _stay_dates(check_in_date: date, check_out_date: date) -> list[date]:
    # Noon check-in/out rule: lock night inventory on [check_in_date, check_out_date).
    total_nights = (check_out_date - check_in_date).days
    return [check_in_date + timedelta(days=offset) for offset in range(total_nights)]


def _validate_booking_dates(check_in_date: date, check_out_date: date) -> int:
    total_nights = (check_out_date - check_in_date).days
    if total_nights <= 0:
        raise ServiceError("check_out_date must be later than check_in_date", status_code=400)
    return total_nights


def create_booking_request(
    db: Session,
    *,
    customer: User | None,
    property_id: int,
    check_in_date: date,
    check_out_date: date,
    guest_count: int,
    guest_name: str,
    guest_phone: str,
    note: str,
) -> Booking:
    # 登录用户必须是 customer 角色；未登录游客允许直接预订
    if customer is not None and customer.role != "customer":
        raise ServiceError("管理员账号不能用于预订，请使用客户账号或以访客身份预订", status_code=403)

    total_nights = _validate_booking_dates(check_in_date, check_out_date)
    if guest_count <= 0:
        raise ServiceError("guest_count must be positive", status_code=400)
    if not guest_name.strip():
        raise ServiceError("guest_name required", status_code=400)
    if not guest_phone.strip():
        raise ServiceError("guest_phone required", status_code=400)

    listing = get_property_by_id(db, property_id=property_id)
    if not listing or not listing.is_active:
        raise ServiceError("property not found", status_code=404)
    if guest_count > listing.max_guests:
        raise ServiceError("guest_count exceeds property max_guests", status_code=400)

    conflict_dates = list_locked_dates(
        db,
        property_id=property_id,
        start_date=check_in_date,
        end_date=check_out_date,
    )
    if conflict_dates:
        dates = [d.isoformat() for d in conflict_dates]
        raise ServiceError(f"dates already locked: {', '.join(dates)}", status_code=409)

    booking = create_booking(
        db,
        property_id=property_id,
        customer_id=customer.id if customer is not None else None,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        total_nights=total_nights,
        guest_count=guest_count,
        guest_name=guest_name.strip(),
        guest_phone=guest_phone.strip(),
        note=note.strip(),
    )
    db.commit()
    db.refresh(booking)
    return booking


def list_my_bookings(db: Session, *, customer: User) -> list[Booking]:
    if customer.role != "customer":
        raise ServiceError("customer only", status_code=403)
    return list_customer_bookings(db, customer_id=customer.id)


def list_admin_pending_bookings(db: Session, *, admin: User) -> list[Booking]:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)
    return list_pending_bookings(db)


def list_all_admin_bookings(db: Session, *, admin: User) -> list[Booking]:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)
    return list_all_bookings(db)


def review_booking_request(
    db: Session,
    *,
    admin: User,
    booking_id: int,
    approve: bool,
    payment_received: bool,
    review_note: str,
) -> Booking:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)

    booking = get_booking_by_id(db, booking_id=booking_id)
    if not booking:
        raise ServiceError("booking not found", status_code=404)

    if booking.status != "pending_review":
        raise ServiceError("booking is already reviewed", status_code=409)

    booking.reviewed_by_admin_id = admin.id
    booking.review_note = review_note.strip()

    if not approve:
        booking.status = "rejected"
        booking.payment_received = payment_received
        booking.reviewed_at = utcnow_naive()
        db.commit()
        db.refresh(booking)
        return booking

    if not payment_received:
        raise ServiceError("payment_received must be true when approving", status_code=400)

    conflict_dates = list_locked_dates(
        db,
        property_id=booking.property_id,
        start_date=booking.check_in_date,
        end_date=booking.check_out_date,
    )
    if conflict_dates:
        dates = [d.isoformat() for d in conflict_dates]
        raise ServiceError(f"dates already locked: {', '.join(dates)}", status_code=409)

    booking.status = "confirmed"
    booking.payment_received = True
    booking.payment_confirmed_at = utcnow_naive()
    booking.reviewed_at = utcnow_naive()

    stay_dates = _stay_dates(booking.check_in_date, booking.check_out_date)
    create_night_locks(db, property_id=booking.property_id, booking_id=booking.id, stay_dates=stay_dates)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ServiceError("dates already locked by another review", status_code=409) from None

    db.refresh(booking)
    return booking
