from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from benreel_api.models import VideoItem
from benreel_api.schemas.video_item import VideoItemStatus


def list_video_items(db: Session, *, status: VideoItemStatus | None = None) -> list[VideoItem]:
    stmt = select(VideoItem).order_by(VideoItem.library_order.asc(), VideoItem.id.asc())
    if status:
        stmt = stmt.where(VideoItem.status == status)
    return list(db.execute(stmt).scalars().all())


def list_video_items_by_external_ids(db: Session, external_ids: list[str]) -> list[VideoItem]:
    if not external_ids:
        return []
    stmt = select(VideoItem).where(VideoItem.external_id.in_(external_ids))
    return list(db.execute(stmt).scalars().all())


def list_video_items_by_asset_urls(db: Session, asset_urls: list[str]) -> list[VideoItem]:
    if not asset_urls:
        return []
    stmt = select(VideoItem).where(VideoItem.asset_url.in_(asset_urls))
    return list(db.execute(stmt).scalars().all())


def get_video_item(db: Session, video_id: int) -> VideoItem | None:
    stmt = select(VideoItem).where(VideoItem.id == video_id)
    return db.execute(stmt).scalars().first()
