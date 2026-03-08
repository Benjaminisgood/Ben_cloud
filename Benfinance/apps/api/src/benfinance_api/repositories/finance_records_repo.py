from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from ..models import FinanceRecord
from ..schemas.finance_record import FinanceRecordCreate, FinanceRecordReview, FinanceRecordUpdate


def _apply_filters(
    stmt: Select[tuple[FinanceRecord]],
    *,
    record_type: str | None,
    planning_status: str | None,
    category: str | None,
    risk_level: str | None,
) -> Select[tuple[FinanceRecord]]:
    if record_type:
        stmt = stmt.where(FinanceRecord.record_type == record_type)
    if planning_status:
        stmt = stmt.where(FinanceRecord.planning_status == planning_status)
    if category:
        stmt = stmt.where(FinanceRecord.category == category)
    if risk_level:
        stmt = stmt.where(FinanceRecord.risk_level == risk_level)
    return stmt


def _apply_visibility(
    stmt: Select[tuple[FinanceRecord]],
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    review_status: str | None,
) -> Select[tuple[FinanceRecord]]:
    if viewer_is_admin:
        if review_status:
            stmt = stmt.where(FinanceRecord.review_status == review_status)
        return stmt

    if review_status:
        if review_status == "approved":
            stmt = stmt.where(or_(FinanceRecord.review_status == "approved", FinanceRecord.created_by == viewer_username))
        else:
            stmt = stmt.where(
                FinanceRecord.created_by == viewer_username,
                FinanceRecord.review_status == review_status,
            )
        return stmt

    return stmt.where(or_(FinanceRecord.review_status == "approved", FinanceRecord.created_by == viewer_username))


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
) -> list[FinanceRecord]:
    stmt = select(FinanceRecord).order_by(FinanceRecord.updated_at.desc(), FinanceRecord.id.desc())
    stmt = _apply_filters(
        stmt,
        record_type=record_type,
        planning_status=planning_status,
        category=category,
        risk_level=risk_level,
    )
    stmt = _apply_visibility(
        stmt,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        review_status=review_status,
    )
    return list(db.execute(stmt.limit(limit)).scalars().all())


def get_finance_record(db: Session, *, record_id: int) -> FinanceRecord | None:
    return db.get(FinanceRecord, record_id)


def create_finance_record(
    db: Session,
    *,
    payload: FinanceRecordCreate,
    actor: str,
    actor_role: str,
) -> FinanceRecord:
    is_admin = actor_role == "admin"
    item = FinanceRecord(
        **payload.model_dump(),
        review_status="approved" if is_admin else "pending_review",
        created_by=actor,
        updated_by=actor,
        reviewed_by=actor if is_admin else None,
        reviewed_at=datetime.now(UTC) if is_admin else None,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_finance_record(
    db: Session,
    *,
    item: FinanceRecord,
    payload: FinanceRecordUpdate,
    actor: str,
) -> FinanceRecord:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_finance_record(db: Session, *, item: FinanceRecord) -> None:
    db.delete(item)
    db.commit()


def review_finance_record(
    db: Session,
    *,
    item: FinanceRecord,
    payload: FinanceRecordReview,
    actor: str,
) -> FinanceRecord:
    item.review_status = payload.review_status
    item.review_note = payload.review_note
    item.reviewed_by = actor
    item.reviewed_at = datetime.now(UTC)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
