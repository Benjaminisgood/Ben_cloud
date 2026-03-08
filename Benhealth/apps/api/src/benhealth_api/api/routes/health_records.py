from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from benhealth_api.api.deps import require_admin, require_user
from benhealth_api.db.session import get_db
from benhealth_api.schemas.health_record import HealthRecordCreate, HealthRecordRead, HealthRecordReview, HealthRecordUpdate
from benhealth_api.services.health_records import (
    create_health_record,
    delete_health_record,
    list_health_records,
    reject_health_record,
    require_health_record,
    review_health_record,
    update_health_record,
)

router = APIRouter(tags=["health_records"])


@router.get("/health-records", response_model=list[HealthRecordRead])
def get_health_records(
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
    domain: str | None = Query(default=None),
    care_status: str | None = Query(default=None),
    concern_level: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[HealthRecordRead]:
    return list_health_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        domain=domain,
        care_status=care_status,
        concern_level=concern_level,
        review_status=review_status,
        limit=limit,
    )


@router.post("/health-records", response_model=HealthRecordRead, status_code=status.HTTP_201_CREATED)
def post_health_record(
    payload: HealthRecordCreate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> HealthRecordRead:
    return create_health_record(db, payload=payload, actor=user["username"], actor_role=user["role"])


@router.get("/health-records/{record_id}", response_model=HealthRecordRead)
def get_health_record_detail(
    record_id: int,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> HealthRecordRead:
    return require_health_record(
        db,
        record_id=record_id,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
    )


@router.patch("/health-records/{record_id}", response_model=HealthRecordRead)
def patch_health_record(
    record_id: int,
    payload: HealthRecordUpdate,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HealthRecordRead:
    return update_health_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.post("/health-records/{record_id}/review", response_model=HealthRecordRead)
def post_health_record_review(
    record_id: int,
    payload: HealthRecordReview,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> HealthRecordRead | Response:
    if payload.review_status == "rejected":
        reject_health_record(db, record_id=record_id, actor=user["username"])
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return review_health_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.delete("/health-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_health_record(
    record_id: int,
    _: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_health_record(db, record_id=record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
