from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from ..models import HealthRecord
from ..schemas.health_record import HealthRecordCreate, HealthRecordReview, HealthRecordUpdate


def _apply_filters(
    stmt: Select[tuple[HealthRecord]],
    *,
    domain: str | None,
    care_status: str | None,
    concern_level: str | None,
) -> Select[tuple[HealthRecord]]:
    if domain:
        stmt = stmt.where(HealthRecord.domain == domain)
    if care_status:
        stmt = stmt.where(HealthRecord.care_status == care_status)
    if concern_level:
        stmt = stmt.where(HealthRecord.concern_level == concern_level)
    return stmt


def _apply_visibility(
    stmt: Select[tuple[HealthRecord]],
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    review_status: str | None,
) -> Select[tuple[HealthRecord]]:
    if viewer_is_admin:
        if review_status:
            stmt = stmt.where(HealthRecord.review_status == review_status)
        return stmt

    if review_status:
        if review_status == "approved":
            stmt = stmt.where(or_(HealthRecord.review_status == "approved", HealthRecord.created_by == viewer_username))
        else:
            stmt = stmt.where(
                HealthRecord.created_by == viewer_username,
                HealthRecord.review_status == review_status,
            )
        return stmt

    return stmt.where(or_(HealthRecord.review_status == "approved", HealthRecord.created_by == viewer_username))


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
) -> list[HealthRecord]:
    stmt = select(HealthRecord).order_by(HealthRecord.updated_at.desc(), HealthRecord.id.desc())
    stmt = _apply_filters(stmt, domain=domain, care_status=care_status, concern_level=concern_level)
    stmt = _apply_visibility(
        stmt,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        review_status=review_status,
    )
    return list(db.execute(stmt.limit(limit)).scalars().all())


def get_health_record(db: Session, *, record_id: int) -> HealthRecord | None:
    return db.get(HealthRecord, record_id)


def create_health_record(
    db: Session,
    *,
    payload: HealthRecordCreate,
    actor: str,
    actor_role: str,
) -> HealthRecord:
    is_admin = actor_role == "admin"
    item = HealthRecord(
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


def update_health_record(
    db: Session,
    *,
    item: HealthRecord,
    payload: HealthRecordUpdate,
    actor: str,
) -> HealthRecord:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_health_record(db: Session, *, item: HealthRecord) -> None:
    db.delete(item)
    db.commit()


def review_health_record(
    db: Session,
    *,
    item: HealthRecord,
    payload: HealthRecordReview,
    actor: str,
) -> HealthRecord:
    item.review_status = payload.review_status
    item.review_note = payload.review_note
    item.reviewed_by = actor
    item.reviewed_at = datetime.now(UTC)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
