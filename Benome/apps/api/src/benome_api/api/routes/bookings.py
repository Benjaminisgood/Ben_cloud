from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from ...models import User
from ...repositories.users_repo import get_user_by_id
from ...schemas.booking import BookingCreateRequest, BookingDetailOut, BookingOut, BookingReviewRequest
from ...services.bookings import (
    cancel_booking_request,
    create_booking_request,
    get_booking_detail,
    list_all_admin_bookings,
    list_admin_pending_bookings,
    list_my_bookings,
    review_booking_request,
)
from ...services.errors import ServiceError
from ..deps import get_current_admin, get_current_customer, get_current_user, get_db

router = APIRouter(tags=["bookings"])


def _to_booking_out(item) -> BookingOut:
    return BookingOut(
        id=item.id,
        property_id=item.property_id,
        customer_id=item.customer_id,
        check_in_date=item.check_in_date,
        check_out_date=item.check_out_date,
        total_nights=item.total_nights,
        guest_count=item.guest_count,
        guest_name=item.guest_name,
        guest_phone=item.guest_phone,
        note=item.note,
        status=item.status,
        payment_received=item.payment_received,
        payment_confirmed_at=item.payment_confirmed_at,
        review_note=item.review_note,
        reviewed_by_admin_id=item.reviewed_by_admin_id,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _to_booking_detail_out(item, property_info=None) -> BookingDetailOut:
    """转换为增强的预订详情响应"""
    from ...models import Property
    
    # 计算总价格
    total_price = None
    price_per_night = None
    property_title = None
    property_address = None
    property_cover = None
    
    if property_info:
        price_per_night = property_info.price_per_night
        total_price = property_info.price_per_night * item.total_nights
        property_title = property_info.title
        property_address = property_info.address
        # 获取封面图片
        if hasattr(property_info, 'media') and property_info.media:
            for media in property_info.media:
                if media.is_cover:
                    property_cover = getattr(media, "public_url", None) or getattr(media, "oss_url", None)
                    break
    
    return BookingDetailOut(
        id=item.id,
        property_id=item.property_id,
        customer_id=item.customer_id,
        check_in_date=item.check_in_date,
        check_out_date=item.check_out_date,
        total_nights=item.total_nights,
        guest_count=item.guest_count,
        guest_name=item.guest_name,
        guest_phone=item.guest_phone,
        note=item.note,
        status=item.status,
        payment_received=item.payment_received,
        payment_confirmed_at=item.payment_confirmed_at,
        review_note=item.review_note,
        reviewed_by_admin_id=item.reviewed_by_admin_id,
        reviewed_at=item.reviewed_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
        property_title=property_title,
        property_address=property_address,
        property_cover=property_cover,
        price_per_night=price_per_night,
        total_price=total_price,
    )


def _resolve_optional_customer(x_user_id: str | None, db: Session) -> User | None:
    """解析可选的 X-User-Id 头，返回 User 或 None（访客）。"""
    if not x_user_id or not x_user_id.isdigit():
        return None
    user = get_user_by_id(db, user_id=int(x_user_id))
    return user if (user and user.is_active) else None


@router.post("/bookings", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking_api(
    payload: BookingCreateRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    db: Session = Depends(get_db),
):
    """创建预订。已登录客户账号时关联账号，否则作为访客预订（无需登录）。"""
    customer = _resolve_optional_customer(x_user_id, db)
    try:
        item = create_booking_request(
            db,
            customer=customer,
            property_id=payload.property_id,
            check_in_date=payload.check_in_date,
            check_out_date=payload.check_out_date,
            guest_count=payload.guest_count,
            guest_name=payload.guest_name,
            guest_phone=payload.guest_phone,
            note=payload.note,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_booking_out(item)


@router.get("/bookings/me", response_model=list[BookingOut])
def my_bookings_api(
    customer: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    try:
        items = list_my_bookings(db, customer=customer)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return [_to_booking_out(item) for item in items]


@router.get("/admin/bookings/all", response_model=list[BookingOut])
def admin_all_bookings_api(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """获取所有预订（管理员专用）"""
    try:
        items = list_all_admin_bookings(db, admin=admin)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return [_to_booking_out(item) for item in items]


@router.get("/admin/bookings/pending", response_model=list[BookingOut])
def admin_pending_bookings_api(
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        items = list_admin_pending_bookings(db, admin=admin)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return [_to_booking_out(item) for item in items]


@router.patch("/admin/bookings/{booking_id}/review", response_model=BookingOut)
def review_booking_api(
    booking_id: int,
    payload: BookingReviewRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        item = review_booking_request(
            db,
            admin=admin,
            booking_id=booking_id,
            approve=payload.approve,
            payment_received=payload.payment_received,
            review_note=payload.review_note,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_booking_out(item)


@router.get("/bookings/{booking_id}", response_model=BookingDetailOut)
def get_booking_detail_api(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取预订详情。客户可以查看自己的预订，管理员可以查看所有预订。"""
    try:
        from ...repositories.properties_repo import get_property_by_id

        item = get_booking_detail(db, booking_id=booking_id, customer=current_user)

        # 获取房源信息
        property_info = get_property_by_id(db, property_id=item.property_id)

        return _to_booking_detail_out(item, property_info)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.post("/bookings/{booking_id}/cancel", response_model=BookingOut)
def cancel_booking_api(
    booking_id: int,
    customer: User = Depends(get_current_customer),
    db: Session = Depends(get_db),
):
    """取消预订。只有待审核状态的预订可以取消。"""
    try:
        item = cancel_booking_request(
            db,
            booking_id=booking_id,
            customer=customer,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return _to_booking_out(item)
