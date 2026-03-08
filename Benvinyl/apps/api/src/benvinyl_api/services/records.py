from __future__ import annotations

import random
from datetime import UTC, date, datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..models import VinylRecord
from ..repositories.records_repo import (
    get_record_by_id,
    get_record_by_oss_path,
    list_candidate_records,
    list_records,
    list_selected_records,
)
from ..schemas.record import VinylRecordCreate, VinylRecordRead, VinylRecordUpdate
from .oss_sync import normalize_oss_path


class DuplicateVinylRecordError(ValueError):
    pass


class VinylRecordNotFoundError(LookupError):
    pass


def _daily_limit() -> int:
    return max(get_settings().DAILY_RECORD_COUNT, 1)


def resolve_audio_url(settings: Settings, oss_path: str) -> str:
    if oss_path.startswith(("http://", "https://")):
        return oss_path
    base = settings.OSS_PUBLIC_BASE_URL
    if base:
        return f"{base}/{normalize_oss_path(settings, oss_path).lstrip('/')}"
    return oss_path


def _derive_title(oss_path: str) -> str:
    parsed = urlparse(oss_path)
    filename = parsed.path.rsplit("/", 1)[-1]
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]
    filename = filename.replace("-", " ").replace("_", " ").strip()
    return filename[:120] or "未命名唱片"


def _serialize_record(record: VinylRecord) -> VinylRecordRead:
    settings = get_settings()
    return VinylRecordRead(
        id=record.id,
        title=record.title,
        note=record.note,
        oss_path=record.oss_path,
        audio_url=resolve_audio_url(settings, record.oss_path),
        added_by=record.added_by,
        is_trashed=record.is_trashed,
        selected_for_date=record.selected_for_date,
        tossed_at=record.tossed_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def list_record_inventory(db: Session) -> list[VinylRecordRead]:
    return [_serialize_record(record) for record in list_records(db)]


def ensure_daily_selection(db: Session, *, display_date: date | None = None) -> None:
    target_date = display_date or date.today()
    daily_limit = _daily_limit()
    current_visible = list_selected_records(db, display_date=target_date, include_trashed=False)
    if len(current_visible) >= daily_limit:
        return

    selected_today = list_selected_records(db, display_date=target_date, include_trashed=True)
    excluded_ids = {record.id for record in selected_today}
    candidates = list_candidate_records(db, display_date=target_date, exclude_ids=excluded_ids)
    if not candidates:
        return

    rng = random.Random(f"benvinyl:{target_date.isoformat()}")
    candidates = sorted(candidates, key=lambda record: (record.created_at, record.id))
    rng.shuffle(candidates)
    remaining = daily_limit - len(current_visible)
    for record in candidates[:remaining]:
        record.selected_for_date = target_date
    db.commit()


def create_record(
    db: Session,
    *,
    payload: VinylRecordCreate,
    added_by: str,
    display_date: date | None = None,
) -> VinylRecordRead:
    settings = get_settings()
    normalized_oss_path = normalize_oss_path(settings, payload.oss_path)
    if not normalized_oss_path:
        raise ValueError("oss_path_required")
    if get_record_by_oss_path(db, normalized_oss_path):
        raise DuplicateVinylRecordError(normalized_oss_path)

    target_date = display_date or date.today()
    current_visible = list_selected_records(db, display_date=target_date, include_trashed=False)
    record = VinylRecord(
        title=payload.title or _derive_title(normalized_oss_path),
        note=payload.note,
        oss_path=normalized_oss_path,
        added_by=added_by,
        is_trashed=False,
        selected_for_date=target_date if len(current_visible) < _daily_limit() else None,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return _serialize_record(record)


def update_record(
    db: Session,
    *,
    record_id: int,
    payload: VinylRecordUpdate,
    display_date: date | None = None,
) -> VinylRecordRead:
    record = get_record_by_id(db, record_id)
    if record is None:
        raise VinylRecordNotFoundError(record_id)

    target_date = display_date or date.today()
    current_visible = [item for item in list_selected_records(db, display_date=target_date, include_trashed=False) if item.id != record.id]

    if payload.is_trashed is True:
        record.is_trashed = True
        record.tossed_at = datetime.now(UTC)
    elif payload.is_trashed is False:
        record.is_trashed = False
        record.tossed_at = None
        record.selected_for_date = target_date
        if len(current_visible) >= _daily_limit():
            demoted = sorted(current_visible, key=lambda item: (item.updated_at, item.id), reverse=True)[0]
            demoted.selected_for_date = None

    db.commit()
    ensure_daily_selection(db, display_date=target_date)
    db.refresh(record)
    return _serialize_record(record)
