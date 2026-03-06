from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...models import User
from ...services.errors import ServiceError
from ...services.statistics import (
    get_booking_statistics as build_booking_statistics,
    get_overview_statistics as build_overview_statistics,
    get_property_statistics as build_property_statistics,
    get_revenue_statistics as build_revenue_statistics,
)
from ..deps import get_current_admin, get_db

router = APIRouter(tags=["statistics"])


@router.get("/statistics/overview")
def get_overview_statistics(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """获取平台概览统计数据"""
    return build_overview_statistics(db)


@router.get("/statistics/properties")
def get_property_statistics(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """获取房源相关统计"""
    return build_property_statistics(db)


@router.get("/statistics/bookings")
def get_booking_statistics(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    days: int = Query(default=30, description="统计最近 N 天的数据"),
):
    """获取预订相关统计"""
    try:
        return build_booking_statistics(db, days=days)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.get("/statistics/revenue")
def get_revenue_statistics(
    _admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    months: int = Query(default=12, description="统计最近 N 个月的数据"),
):
    """获取收入相关统计"""
    try:
        return build_revenue_statistics(db, months=months)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
