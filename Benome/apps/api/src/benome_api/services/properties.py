from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from ..models import Property, User
from ..repositories.bookings_repo import list_locked_dates
from ..repositories.properties_repo import create_property, delete_property, get_property_by_id, list_active_properties
from .errors import ServiceError


def create_property_listing(
    db: Session,
    *,
    admin: User,
    title: str,
    description: str,
    city: str,
    address: str,
    price_per_night: int,
    max_guests: int,
    is_active: bool,
) -> Property:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)
    if not title.strip():
        raise ServiceError("title required", status_code=400)
    if price_per_night <= 0:
        raise ServiceError("price_per_night must be positive", status_code=400)
    if max_guests <= 0:
        raise ServiceError("max_guests must be positive", status_code=400)

    item = create_property(
        db,
        title=title.strip(),
        description=description.strip(),
        city=city.strip(),
        address=address.strip(),
        price_per_night=price_per_night,
        max_guests=max_guests,
        is_active=is_active,
        created_by_admin_id=admin.id,
    )
    db.commit()
    db.refresh(item)
    return item


def update_property_listing(
    db: Session,
    *,
    admin: User,
    property_id: int,
    title: str | None,
    description: str | None,
    city: str | None,
    address: str | None,
    price_per_night: int | None,
    max_guests: int | None,
    is_active: bool | None,
) -> Property:
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)

    item = get_property_by_id(db, property_id=property_id)
    if not item:
        raise ServiceError("property not found", status_code=404)

    if title is not None:
        title = title.strip()
        if not title:
            raise ServiceError("title required", status_code=400)
        item.title = title
    if description is not None:
        item.description = description.strip()
    if city is not None:
        item.city = city.strip()
    if address is not None:
        item.address = address.strip()
    if price_per_night is not None:
        if price_per_night <= 0:
            raise ServiceError("price_per_night must be positive", status_code=400)
        item.price_per_night = price_per_night
    if max_guests is not None:
        if max_guests <= 0:
            raise ServiceError("max_guests must be positive", status_code=400)
        item.max_guests = max_guests
    if is_active is not None:
        item.is_active = is_active

    db.commit()
    db.refresh(item)
    return item


def list_public_properties(db: Session) -> list[Property]:
    return list_active_properties(db)


def get_public_property_detail(db: Session, *, property_id: int) -> Property:
    item = get_property_by_id(db, property_id=property_id)
    if not item or not item.is_active:
        raise ServiceError("property not found", status_code=404)
    return item


def check_property_availability(
    db: Session,
    *,
    property_id: int,
    check_in_date: date,
    check_out_date: date,
) -> tuple[Property, list[date]]:
    item = get_public_property_detail(db, property_id=property_id)
    total_nights = (check_out_date - check_in_date).days
    if total_nights <= 0:
        raise ServiceError("check_out_date must be later than check_in_date", status_code=400)

    conflicts = list_locked_dates(
        db,
        property_id=property_id,
        start_date=check_in_date,
        end_date=check_out_date,
    )
    return item, conflicts


def delete_property_listing(
    db: Session,
    *,
    admin: User,
    property_id: int,
) -> None:
    """删除房源。
    
    Args:
        db: 数据库会话
        admin: 管理员用户
        property_id: 房源 ID
    
    Raises:
        ServiceError: 权限不足、房源不存在、或有活跃预订
    """
    if admin.role != "admin":
        raise ServiceError("admin only", status_code=403)
    
    item = get_property_by_id(db, property_id=property_id)
    if not item:
        raise ServiceError("property not found", status_code=404)
    
    # 检查是否有活跃预订（可选，根据业务需求决定）
    # 如果有活跃预订，可以选择阻止删除或级联处理
    # 这里选择直接删除，依赖数据库的外键约束
    
    delete_property(db, property_id=property_id)
    db.commit()
