from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from benvinyl_api.api.deps import require_admin_user
from benvinyl_api.db.session import get_db
from benvinyl_api.schemas.record import VinylRecordCreate, VinylRecordRead, VinylRecordUpdate
from benvinyl_api.services.records import (
    DuplicateVinylRecordError,
    VinylRecordNotFoundError,
    create_record,
    list_record_inventory,
    update_record,
)
from benvinyl_api.services.oss_sync import sync_missing_records_from_oss

router = APIRouter(tags=["records"])


@router.get("/records", response_model=list[VinylRecordRead])
def get_records(
    _: dict[str, str] = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> list[VinylRecordRead]:
    sync_missing_records_from_oss(db)
    return list_record_inventory(db)


@router.post("/records", response_model=VinylRecordRead, status_code=status.HTTP_201_CREATED)
def post_record(
    payload: VinylRecordCreate,
    user: dict[str, str] = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> VinylRecordRead:
    try:
        return create_record(db, payload=payload, added_by=user["username"])
    except DuplicateVinylRecordError as exc:
        raise HTTPException(status_code=409, detail="record_exists") from exc


@router.patch("/records/{record_id}", response_model=VinylRecordRead)
def patch_record(
    record_id: int,
    payload: VinylRecordUpdate,
    _: dict[str, str] = Depends(require_admin_user),
    db: Session = Depends(get_db),
) -> VinylRecordRead:
    try:
        return update_record(db, record_id=record_id, payload=payload)
    except VinylRecordNotFoundError as exc:
        raise HTTPException(status_code=404, detail="record_not_found") from exc
