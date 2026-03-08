from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..repositories.preference_records_repo import (
    create_preference_record as repo_create_preference_record,
    delete_preference_record as repo_delete_preference_record,
    get_preference_record,
    list_preference_records as repo_list_preference_records,
    review_preference_record as repo_review_preference_record,
    update_preference_record as repo_update_preference_record,
)
from ..schemas.preference_record import PreferenceRecordCreate, PreferenceRecordReview, PreferenceRecordUpdate


def list_preference_records(
    db: Session,
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    subject_type: str | None = None,
    stance: str | None = None,
    timeframe: str | None = None,
    validation_state: str | None = None,
    review_status: str | None = None,
    limit: int = 50,
):
    return repo_list_preference_records(
        db,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        subject_type=subject_type,
        stance=stance,
        timeframe=timeframe,
        validation_state=validation_state,
        review_status=review_status,
        limit=limit,
    )


def create_preference_record(db: Session, *, payload: PreferenceRecordCreate, actor: str, actor_role: str):
    return repo_create_preference_record(db, payload=payload, actor=actor, actor_role=actor_role)


def require_preference_record(
    db: Session,
    *,
    record_id: int,
    viewer_username: str,
    viewer_is_admin: bool,
):
    item = get_preference_record(db, record_id=record_id)
    if not item:
        raise HTTPException(status_code=404, detail="preference_record_not_found")
    if not viewer_is_admin and item.review_status != "approved" and item.created_by != viewer_username:
        raise HTTPException(status_code=404, detail="preference_record_not_found")
    return item


def update_preference_record(db: Session, *, record_id: int, payload: PreferenceRecordUpdate, actor: str):
    item = require_preference_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_update_preference_record(db, item=item, payload=payload, actor=actor)


def delete_preference_record(db: Session, *, record_id: int) -> None:
    item = require_preference_record(db, record_id=record_id, viewer_username="", viewer_is_admin=True)
    repo_delete_preference_record(db, item=item)


def review_preference_record(db: Session, *, record_id: int, payload: PreferenceRecordReview, actor: str):
    item = require_preference_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_review_preference_record(db, item=item, payload=payload, actor=actor)


def reject_preference_record(db: Session, *, record_id: int, actor: str) -> None:
    item = require_preference_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    repo_delete_preference_record(db, item=item)
