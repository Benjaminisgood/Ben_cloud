from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from benjournal_api.models import JournalAudioSegment


def list_segments_for_day(db: Session, *, journal_day_id: int) -> list[JournalAudioSegment]:
    stmt = (
        select(JournalAudioSegment)
        .where(JournalAudioSegment.journal_day_id == journal_day_id)
        .order_by(JournalAudioSegment.sequence_no.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_next_sequence_no(db: Session, *, journal_day_id: int) -> int:
    stmt = select(func.coalesce(func.max(JournalAudioSegment.sequence_no), 0)).where(
        JournalAudioSegment.journal_day_id == journal_day_id
    )
    current = db.execute(stmt).scalar_one()
    return int(current or 0) + 1


def create_segment(
    db: Session,
    *,
    journal_day_id: int,
    sequence_no: int,
    original_filename: str,
    file_extension: str,
    mime_type: str,
    local_path: str,
    byte_size: int,
    username: str,
) -> JournalAudioSegment:
    item = JournalAudioSegment(
        journal_day_id=journal_day_id,
        sequence_no=sequence_no,
        original_filename=original_filename,
        file_extension=file_extension,
        mime_type=mime_type,
        local_path=local_path,
        byte_size=byte_size,
        created_by=username,
    )
    db.add(item)
    db.flush()
    return item
