from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from ..models import PreferenceRecord
from ..schemas.preference_record import PreferenceRecordCreate, PreferenceRecordReview, PreferenceRecordUpdate


def _apply_filters(
    stmt: Select[tuple[PreferenceRecord]],
    *,
    subject_type: str | None,
    stance: str | None,
    timeframe: str | None,
    validation_state: str | None,
) -> Select[tuple[PreferenceRecord]]:
    if subject_type:
        stmt = stmt.where(PreferenceRecord.subject_type == subject_type)
    if stance:
        stmt = stmt.where(PreferenceRecord.stance == stance)
    if timeframe:
        stmt = stmt.where(PreferenceRecord.timeframe == timeframe)
    if validation_state:
        stmt = stmt.where(PreferenceRecord.validation_state == validation_state)
    return stmt


def _apply_visibility(
    stmt: Select[tuple[PreferenceRecord]],
    *,
    viewer_username: str,
    viewer_is_admin: bool,
    review_status: str | None,
) -> Select[tuple[PreferenceRecord]]:
    if viewer_is_admin:
        if review_status:
            stmt = stmt.where(PreferenceRecord.review_status == review_status)
        return stmt

    if review_status:
        if review_status == "approved":
            stmt = stmt.where(
                or_(
                    PreferenceRecord.review_status == "approved",
                    PreferenceRecord.created_by == viewer_username,
                )
            )
        else:
            stmt = stmt.where(
                PreferenceRecord.created_by == viewer_username,
                PreferenceRecord.review_status == review_status,
            )
        return stmt

    return stmt.where(
        or_(
            PreferenceRecord.review_status == "approved",
            PreferenceRecord.created_by == viewer_username,
        )
    )


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
) -> list[PreferenceRecord]:
    stmt = select(PreferenceRecord).order_by(PreferenceRecord.updated_at.desc(), PreferenceRecord.id.desc())
    stmt = _apply_filters(
        stmt,
        subject_type=subject_type,
        stance=stance,
        timeframe=timeframe,
        validation_state=validation_state,
    )
    stmt = _apply_visibility(
        stmt,
        viewer_username=viewer_username,
        viewer_is_admin=viewer_is_admin,
        review_status=review_status,
    )
    return list(db.execute(stmt.limit(limit)).scalars().all())


def get_preference_record(db: Session, *, record_id: int) -> PreferenceRecord | None:
    return db.get(PreferenceRecord, record_id)


def create_preference_record(
    db: Session,
    *,
    payload: PreferenceRecordCreate,
    actor: str,
    actor_role: str,
) -> PreferenceRecord:
    is_admin = actor_role == "admin"
    item = PreferenceRecord(
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


def update_preference_record(
    db: Session,
    *,
    item: PreferenceRecord,
    payload: PreferenceRecordUpdate,
    actor: str,
) -> PreferenceRecord:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def delete_preference_record(db: Session, *, item: PreferenceRecord) -> None:
    db.delete(item)
    db.commit()


def review_preference_record(
    db: Session,
    *,
    item: PreferenceRecord,
    payload: PreferenceRecordReview,
    actor: str,
) -> PreferenceRecord:
    item.review_status = payload.review_status
    item.review_note = payload.review_note
    item.reviewed_by = actor
    item.reviewed_at = datetime.now(UTC)
    item.updated_by = actor
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
