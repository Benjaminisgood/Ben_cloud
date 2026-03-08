from __future__ import annotations

from datetime import UTC, date, datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..models import Photo
from ..repositories.photos_repo import (
    get_photo_by_id,
    get_photo_by_oss_path,
    list_photos,
    list_selected_photos,
)
from ..schemas.photo import PhotoCreate, PhotoRead, PhotoUpdate
from .oss_sync import normalize_oss_path as normalize_media_oss_path


class DuplicatePhotoError(ValueError):
    pass


class PhotoNotFoundError(LookupError):
    pass


def normalize_oss_path(settings: Settings, oss_path: str) -> str:
    return normalize_media_oss_path(settings, oss_path)


def resolve_image_url(settings: Settings, oss_path: str) -> str:
    if oss_path.startswith(("http://", "https://")):
        return oss_path
    base = settings.OSS_PUBLIC_BASE_URL
    if base:
        return f"{base}/{normalize_oss_path(settings, oss_path).lstrip('/')}"
    return oss_path


def _derive_title(oss_path: str) -> str:
    parsed = urlparse(oss_path)
    filename = parsed.path.rsplit("/", 1)[-1]
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]
    filename = filename.replace("-", " ").replace("_", " ").strip()
    return filename[:120] or "未命名相纸"


def _serialize_photo(photo: Photo) -> PhotoRead:
    settings = get_settings()
    return PhotoRead(
        id=photo.id,
        title=photo.title,
        caption=photo.caption,
        oss_path=photo.oss_path,
        image_url=resolve_image_url(settings, photo.oss_path),
        added_by=photo.added_by,
        is_trashed=photo.is_trashed,
        selected_for_date=photo.selected_for_date,
        tossed_at=photo.tossed_at,
        created_at=photo.created_at,
        updated_at=photo.updated_at,
    )


def list_photo_inventory(db: Session) -> list[PhotoRead]:
    return [_serialize_photo(photo) for photo in list_photos(db)]


def create_photo(
    db: Session,
    *,
    payload: PhotoCreate,
    added_by: str,
    display_date: date | None = None,
) -> PhotoRead:
    settings = get_settings()
    normalized_oss_path = normalize_oss_path(settings, payload.oss_path)
    if not normalized_oss_path:
        raise ValueError("oss_path_required")
    if get_photo_by_oss_path(db, normalized_oss_path):
        raise DuplicatePhotoError(normalized_oss_path)

    target_date = display_date or date.today()
    today_selection = list_selected_photos(db, display_date=target_date, include_trashed=True)
    photo = Photo(
        title=payload.title or _derive_title(normalized_oss_path),
        caption=payload.caption,
        oss_path=normalized_oss_path,
        added_by=added_by,
        is_trashed=False,
        selected_for_date=target_date if len(today_selection) < max(settings.DAILY_PHOTO_COUNT, 1) else None,
    )
    db.add(photo)
    db.commit()
    db.refresh(photo)
    return _serialize_photo(photo)


def update_photo(
    db: Session,
    *,
    photo_id: int,
    payload: PhotoUpdate,
    display_date: date | None = None,
) -> PhotoRead:
    settings = get_settings()
    photo = get_photo_by_id(db, photo_id)
    if photo is None:
        raise PhotoNotFoundError(photo_id)

    target_date = display_date or date.today()
    if payload.is_trashed:
        photo.is_trashed = True
        photo.tossed_at = datetime.now(UTC)
    else:
        today_selection = list_selected_photos(db, display_date=target_date, include_trashed=True)
        photo.is_trashed = False
        photo.tossed_at = None
        if photo.selected_for_date is None and len(today_selection) < max(settings.DAILY_PHOTO_COUNT, 1):
            photo.selected_for_date = target_date

    db.commit()
    db.refresh(photo)
    return _serialize_photo(photo)
