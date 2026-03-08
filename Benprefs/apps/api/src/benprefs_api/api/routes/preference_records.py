from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from benprefs_api.api.deps import require_admin, require_user
from benprefs_api.db.session import get_db
from benprefs_api.schemas.preference_record import (
    PreferenceRecordCreate,
    PreferenceRecordRead,
    PreferenceRecordReview,
    PreferenceRecordUpdate,
)
from benprefs_api.services.preference_records import (
    create_preference_record,
    delete_preference_record,
    list_preference_records,
    reject_preference_record,
    require_preference_record,
    review_preference_record,
    update_preference_record,
)

router = APIRouter(tags=["preference_records"])


@router.get("/preference-records", response_model=list[PreferenceRecordRead])
def get_preference_records(
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
    subject_type: str | None = Query(default=None),
    stance: str | None = Query(default=None),
    timeframe: str | None = Query(default=None),
    validation_state: str | None = Query(default=None),
    review_status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PreferenceRecordRead]:
    return list_preference_records(
        db,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
        subject_type=subject_type,
        stance=stance,
        timeframe=timeframe,
        validation_state=validation_state,
        review_status=review_status,
        limit=limit,
    )


@router.post("/preference-records", response_model=PreferenceRecordRead, status_code=status.HTTP_201_CREATED)
def post_preference_record(
    payload: PreferenceRecordCreate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> PreferenceRecordRead:
    return create_preference_record(db, payload=payload, actor=user["username"], actor_role=user["role"])


@router.get("/preference-records/{record_id}", response_model=PreferenceRecordRead)
def get_preference_record_detail(
    record_id: int,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> PreferenceRecordRead:
    return require_preference_record(
        db,
        record_id=record_id,
        viewer_username=user["username"],
        viewer_is_admin=user["role"] == "admin",
    )


@router.patch("/preference-records/{record_id}", response_model=PreferenceRecordRead)
def patch_preference_record(
    record_id: int,
    payload: PreferenceRecordUpdate,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PreferenceRecordRead:
    return update_preference_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.post("/preference-records/{record_id}/review", response_model=PreferenceRecordRead)
def post_preference_record_review(
    record_id: int,
    payload: PreferenceRecordReview,
    user: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> PreferenceRecordRead | Response:
    if payload.review_status == "rejected":
        reject_preference_record(db, record_id=record_id, actor=user["username"])
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return review_preference_record(db, record_id=record_id, payload=payload, actor=user["username"])


@router.delete("/preference-records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_preference_record(
    record_id: int,
    _: dict[str, str] = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Response:
    delete_preference_record(db, record_id=record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
