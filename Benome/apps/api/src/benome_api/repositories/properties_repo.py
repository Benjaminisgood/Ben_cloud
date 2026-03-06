from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Property


def create_property(
    db: Session,
    *,
    title: str,
    description: str,
    city: str,
    address: str,
    price_per_night: int,
    max_guests: int,
    is_active: bool,
    created_by_admin_id: int,
) -> Property:
    item = Property(
        title=title,
        description=description,
        city=city,
        address=address,
        price_per_night=price_per_night,
        max_guests=max_guests,
        is_active=is_active,
        created_by_admin_id=created_by_admin_id,
    )
    db.add(item)
    db.flush()
    return item


def get_property_by_id(db: Session, *, property_id: int) -> Property | None:
    return db.scalar(select(Property).where(Property.id == property_id))


def list_active_properties(db: Session) -> list[Property]:
    return list(db.scalars(select(Property).where(Property.is_active.is_(True)).order_by(Property.id.desc())).all())


def delete_property(db: Session, *, property_id: int) -> None:
    """删除房源。
    
    Args:
        db: 数据库会话
        property_id: 房源 ID
    
    Note:
        依赖数据库的外键级联删除，会自动删除相关的 media 和 booking 记录
    """
    from sqlalchemy import delete
    from ..models import Property
    
    db.execute(delete(Property).where(Property.id == property_id))
