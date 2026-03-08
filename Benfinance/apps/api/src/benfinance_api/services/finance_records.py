from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..repositories.finance_records_repo import (
    create_finance_record as repo_create_finance_record,
    delete_finance_record as repo_delete_finance_record,
    get_finance_record,
    list_finance_records as repo_list_finance_records,
    review_finance_record as repo_review_finance_record,
    update_finance_record as repo_update_finance_record,
)
from ..schemas.finance_record import FinanceRecordCreate, FinanceRecordReview, FinanceRecordUpdate


def list_finance_records(
    db: Session,
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    record_type: str | None = None,
    planning_status: str | None = None,
    category: str | None = None,
    risk_level: str | None = None,
    review_status: str | None = None,
    limit: int = 50,
):
    return repo_list_finance_records(
        db,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        record_type=record_type,
        planning_status=planning_status,
        category=category,
        risk_level=risk_level,
        review_status=review_status,
        limit=limit,
    )


def create_finance_record(db: Session, *, payload: FinanceRecordCreate, actor: str, actor_role: str):
    return repo_create_finance_record(db, payload=payload, actor=actor, actor_role=actor_role)


def require_finance_record(
    db: Session,
    *,
    record_id: int,
    viewer_username: str,
    viewer_is_admin: bool,
):
    item = get_finance_record(db, record_id=record_id)
    if not item:
        raise HTTPException(status_code=404, detail="finance_record_not_found")
    if not viewer_is_admin and item.review_status != "approved" and item.created_by != viewer_username:
        raise HTTPException(status_code=404, detail="finance_record_not_found")
    return item


def update_finance_record(db: Session, *, record_id: int, payload: FinanceRecordUpdate, actor: str):
    item = require_finance_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_update_finance_record(db, item=item, payload=payload, actor=actor)


def delete_finance_record(db: Session, *, record_id: int) -> None:
    item = require_finance_record(db, record_id=record_id, viewer_username="", viewer_is_admin=True)
    repo_delete_finance_record(db, item=item)


def review_finance_record(db: Session, *, record_id: int, payload: FinanceRecordReview, actor: str):
    item = require_finance_record(db, record_id=record_id, viewer_username=actor, viewer_is_admin=True)
    return repo_review_finance_record(db, item=item, payload=payload, actor=actor)
