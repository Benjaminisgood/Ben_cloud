from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..repositories.health_records_repo import (
    create_health_record as repo_create_health_record,
    delete_health_record as repo_delete_health_record,
    get_health_record,
    list_health_records as repo_list_health_records,
    review_health_record as repo_review_health_record,
    update_health_record as repo_update_health_record,
)
from ..schemas.health_record import HealthRecordCreate, HealthRecordReview, HealthRecordUpdate


def list_health_records(
    db: Session,
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    domain: str | None = None,
    care_status: str | None = None,
    concern_level: str | None = None,
    review_status: str | None = None,
    limit: int = 50,
):
    return repo_list_health_records(
        db,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        domain=domain,
        care_status=care_status,
        concern_level=concern_level,
        review_status=review_status,
        limit=limit,
    )


def create_health_record(db: Session, *, payload: HealthRecordCreate, actor: str, actor_role: str):
    return repo_create_health_record(db, payload=payload, actor=actor, actor_role=actor_role)


def require_health_record(
    db: Session,
    *,
    record_id: int,
    viewer_username: str,
    viewer_is_admin: bool,
):
    item = get_health_record(db, record_id=record_id)
    if not item:
        raise HTTPException(status_code=404, detail="health_record_not_found")
    if not viewer_is_admin and item.review_status != "approved" and item.created_by != viewer_username:
        raise HTTPException(status_code=404, detail="health_record_not_found")
    return item


def update_health_record(db: Session, *, record_id: int, payload: HealthRecordUpdate, actor: str):
    item = require_health_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_update_health_record(db, item=item, payload=payload, actor=actor)


def delete_health_record(db: Session, *, record_id: int) -> None:
    item = require_health_record(db, record_id=record_id, viewer_username="", viewer_is_admin=True)
    repo_delete_health_record(db, item=item)


def review_health_record(db: Session, *, record_id: int, payload: HealthRecordReview, actor: str):
    item = require_health_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_review_health_record(db, item=item, payload=payload, actor=actor)


def reject_health_record(db: Session, *, record_id: int, actor: str) -> None:
    item = require_health_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    repo_delete_health_record(db, item=item)
