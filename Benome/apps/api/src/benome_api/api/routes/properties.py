from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...models import User
from ...schemas.property import (
    PropertyAvailabilityOut,
    PropertyCreateRequest,
    PropertyOut,
    PropertyPatchRequest,
)
from ...schemas.property_media import PropertyMediaOut
from ...services.errors import ServiceError
from ...services.property_media import get_property_media_list
from ...services.properties import (
    check_property_availability,
    create_property_listing,
    get_public_property_detail,
    list_public_properties,
    update_property_listing,
)
from ..deps import get_current_admin, get_db

router = APIRouter(tags=["properties"])


def _resolve_cover_image(db: Session, property_id: int) -> str | None:
    media_list = get_property_media_list(db, property_id)
    if not media_list:
        return None
    cover = next((media for media in media_list if media.is_cover and media.public_url), None)
    if cover is not None:
        return cover.public_url
    first_image = next((media for media in media_list if media.public_url), None)
    return first_image.public_url if first_image is not None else None


@router.get("/properties", response_model=list[PropertyOut])
def list_properties(db: Session = Depends(get_db)):
    items = list_public_properties(db)
    return [
        PropertyOut(
            id=item.id,
            title=item.title,
            description=item.description,
            city=item.city,
            address=item.address,
            price_per_night=item.price_per_night,
            max_guests=item.max_guests,
            is_active=item.is_active,
            created_by_admin_id=item.created_by_admin_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
            cover_image=_resolve_cover_image(db, item.id),
        )
        for item in items
    ]


@router.get("/properties/public", response_model=list[PropertyOut])
def list_public_properties_api(db: Session = Depends(get_db)):
    """获取所有公开的房源列表（前端专用）"""
    items = list_public_properties(db)
    return [
        PropertyOut(
            id=item.id,
            title=item.title,
            description=item.description,
            city=item.city,
            address=item.address,
            price_per_night=item.price_per_night,
            max_guests=item.max_guests,
            is_active=item.is_active,
            created_by_admin_id=item.created_by_admin_id,
            created_at=item.created_at,
            updated_at=item.updated_at,
            cover_image=_resolve_cover_image(db, item.id),
        )
        for item in items
    ]


@router.get("/properties/{property_id}", response_model=PropertyOut)
def property_detail(property_id: int, db: Session = Depends(get_db)):
    try:
        item = get_public_property_detail(db, property_id=property_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    # 获取媒体列表
    media_list = get_property_media_list(db, property_id)
    media_out = [
        PropertyMediaOut(
            id=m.id,
            property_id=m.property_id,
            media_type=m.media_type,
            oss_key=m.oss_key,
            public_url=m.public_url,
            file_size=m.file_size,
            mime_type=m.mime_type,
            title=m.title,
            description=m.description,
            sort_order=m.sort_order,
            is_cover=m.is_cover,
            is_active=m.is_active,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
        for m in media_list
    ]

    return PropertyOut(
        id=item.id,
        title=item.title,
        description=item.description,
        city=item.city,
        address=item.address,
        price_per_night=item.price_per_night,
        max_guests=item.max_guests,
        is_active=item.is_active,
        created_by_admin_id=item.created_by_admin_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
        cover_image=_resolve_cover_image(db, item.id),
        media=media_out,
    )


@router.get("/properties/{property_id}/availability", response_model=PropertyAvailabilityOut)
def property_availability(
    property_id: int,
    check_in_date: date,
    check_out_date: date,
    db: Session = Depends(get_db),
):
    try:
        item, conflicts = check_property_availability(
            db,
            property_id=property_id,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return PropertyAvailabilityOut(
        property_id=item.id,
        check_in_date=check_in_date,
        check_out_date=check_out_date,
        total_nights=(check_out_date - check_in_date).days,
        available=not conflicts,
        conflict_dates=conflicts,
    )


@router.post("/admin/properties", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
def create_property_api(
    payload: PropertyCreateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    try:
        item = create_property_listing(
            db,
            admin=admin,
            title=payload.title,
            description=payload.description,
            city=payload.city,
            address=payload.address,
            price_per_night=payload.price_per_night,
            max_guests=payload.max_guests,
            is_active=payload.is_active,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return PropertyOut(
        id=item.id,
        title=item.title,
        description=item.description,
        city=item.city,
        address=item.address,
        price_per_night=item.price_per_night,
        max_guests=item.max_guests,
        is_active=item.is_active,
        created_by_admin_id=item.created_by_admin_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.put("/admin/properties/{property_id}", response_model=PropertyOut)
@router.patch("/admin/properties/{property_id}", response_model=PropertyOut)
def update_property_api(
    property_id: int,
    payload: PropertyPatchRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新房源信息（支持 PUT 和 PATCH 方法）"""
    try:
        item = update_property_listing(
            db,
            admin=admin,
            property_id=property_id,
            title=payload.title,
            description=payload.description,
            city=payload.city,
            address=payload.address,
            price_per_night=payload.price_per_night,
            max_guests=payload.max_guests,
            is_active=payload.is_active,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None

    return PropertyOut(
        id=item.id,
        title=item.title,
        description=item.description,
        city=item.city,
        address=item.address,
        price_per_night=item.price_per_night,
        max_guests=item.max_guests,
        is_active=item.is_active,
        created_by_admin_id=item.created_by_admin_id,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/admin/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property_api(
    property_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除房源"""
    try:
        from ...services.properties import delete_property_listing
        delete_property_listing(db, admin=admin, property_id=property_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
