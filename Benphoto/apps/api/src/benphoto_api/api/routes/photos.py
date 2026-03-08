from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from benphoto_api.api.deps import require_user
from benphoto_api.db.session import get_db
from benphoto_api.schemas.photo import PhotoCreate, PhotoRead, PhotoUpdate
from benphoto_api.services.photos import (
    DuplicatePhotoError,
    PhotoNotFoundError,
    create_photo,
    list_photo_inventory,
    update_photo,
)
from benphoto_api.services.oss_sync import sync_missing_photos_from_oss

router = APIRouter(tags=["photos"])


@router.get("/photos", response_model=list[PhotoRead])
def get_photos(
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[PhotoRead]:
    sync_missing_photos_from_oss(db)
    return list_photo_inventory(db)


@router.post("/photos", response_model=PhotoRead, status_code=status.HTTP_201_CREATED)
def post_photo(
    payload: PhotoCreate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> PhotoRead:
    try:
        return create_photo(db, payload=payload, added_by=user["username"])
    except DuplicatePhotoError as exc:
        raise HTTPException(status_code=409, detail="photo_exists") from exc


@router.patch("/photos/{photo_id}", response_model=PhotoRead)
def patch_photo(
    photo_id: int,
    payload: PhotoUpdate,
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> PhotoRead:
    try:
        return update_photo(db, photo_id=photo_id, payload=payload)
    except PhotoNotFoundError as exc:
        raise HTTPException(status_code=404, detail="photo_not_found") from exc
