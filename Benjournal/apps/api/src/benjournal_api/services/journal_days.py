from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from benjournal_api.core.config import get_settings
from benjournal_api.models import JournalDay
from benjournal_api.repositories.journal_audio_segments_repo import (
    create_segment,
    get_next_sequence_no,
    list_segments_for_day,
)
from benjournal_api.repositories.journal_days_repo import create_day, get_day_by_date, list_recent_days
from benjournal_api.schemas.journal_day import (
    JournalDayListItem,
    JournalDayRead,
    JournalIngestResponse,
)
from benjournal_api.services.audio_merge import AudioMergeError, merge_audio_segments
from benjournal_api.services.storage import StorageError, upload_daily_audio
from benjournal_api.services.stt import STTError, transcribe_audio


class JournalServiceError(RuntimeError):
    pass


def get_journal_day_detail(db: Session, *, entry_date: date) -> JournalDayRead | None:
    day = get_day_by_date(db, entry_date=entry_date)
    if day is None:
        return None
    return serialize_day(day)


def list_recent_journal_days(db: Session, *, limit: int = 14) -> list[JournalDayListItem]:
    return [serialize_list_item(item) for item in list_recent_days(db, limit=limit)]


def update_journal_text(
    db: Session,
    *,
    entry_date: date,
    entry_text: str,
    username: str,
) -> JournalDayRead:
    day = _get_or_create_day(db, entry_date=entry_date, username=username)
    day.entry_text = entry_text.strip()
    day.updated_by = username
    day.last_error_message = ""
    db.commit()
    db.refresh(day)
    return serialize_day(day)


def ingest_audio_segment(
    db: Session,
    *,
    entry_date: date,
    audio_bytes: bytes,
    filename: str,
    content_type: str,
    username: str,
) -> JournalIngestResponse:
    settings = get_settings()
    if not audio_bytes:
        raise JournalServiceError("上传的音频为空。")
    max_bytes = settings.MAX_AUDIO_FILE_SIZE_MB * 1024 * 1024
    if len(audio_bytes) > max_bytes:
        raise JournalServiceError(f"单个音频不能超过 {settings.MAX_AUDIO_FILE_SIZE_MB} MB。")

    extension = _resolve_extension(filename)
    day = _get_or_create_day(db, entry_date=entry_date, username=username)
    sequence_no = get_next_sequence_no(db, journal_day_id=day.id)

    segment_dir = settings.AUDIO_SEGMENTS_DIR / entry_date.isoformat()
    segment_dir.mkdir(parents=True, exist_ok=True)
    segment_path = segment_dir / f"segment-{sequence_no:04d}{extension}"
    segment_path.write_bytes(audio_bytes)

    create_segment(
        db,
        journal_day_id=day.id,
        sequence_no=sequence_no,
        original_filename=filename,
        file_extension=extension,
        mime_type=content_type,
        local_path=str(segment_path),
        byte_size=len(audio_bytes),
        username=username,
    )

    warnings: list[str] = []
    segments = list_segments_for_day(db, journal_day_id=day.id)
    segment_paths = [Path(item.local_path) for item in segments]

    combined_extension = ".wav" if all(path.suffix.lower() == ".wav" for path in segment_paths) else extension
    combined_dir = settings.COMBINED_AUDIO_DIR / entry_date.isoformat()
    combined_dir.mkdir(parents=True, exist_ok=True)
    combined_path = combined_dir / f"{entry_date.isoformat()}-merged{combined_extension}"

    day.segment_count = len(segments)
    day.total_audio_bytes = sum(item.byte_size for item in segments)
    day.updated_by = username
    day.last_recorded_at = datetime.now(UTC)
    day.combined_audio_path = str(combined_path)
    day.last_error_message = ""

    try:
        merge_audio_segments(segment_paths, output_path=combined_path)
    except AudioMergeError as exc:
        message = str(exc)
        day.storage_status = "failed"
        day.transcript_status = "failed"
        day.last_error_message = message
        db.commit()
        db.refresh(day)
        return JournalIngestResponse(day=serialize_day(day), warnings=[message])

    _upload_daily_audio(day, combined_path=combined_path, entry_date=entry_date, warnings=warnings)
    _refresh_transcript(day, combined_path=combined_path, entry_date=entry_date, warnings=warnings)

    if warnings:
        day.last_error_message = "；".join(warnings)
    else:
        day.last_error_message = ""

    db.commit()
    db.refresh(day)
    return JournalIngestResponse(day=serialize_day(day), warnings=warnings)


def serialize_day(day: JournalDay) -> JournalDayRead:
    payload = JournalDayRead.model_validate(day)
    payload.playback_url = (
        f"/journal-days/{payload.entry_date.isoformat()}/audio"
        if getattr(day, "combined_audio_path", None)
        else None
    )
    payload.segments = sorted(payload.segments, key=lambda item: item.sequence_no)
    return payload


def serialize_list_item(day: JournalDay) -> JournalDayListItem:
    preview_source = (day.entry_text or day.stt_text or "").strip()
    preview = preview_source[:96] + ("..." if len(preview_source) > 96 else "")
    return JournalDayListItem(
        entry_date=day.entry_date.isoformat(),
        segment_count=day.segment_count,
        transcript_status=day.transcript_status,
        storage_status=day.storage_status,
        updated_at=day.updated_at,
        transcript_preview=preview or "当天还没有文本内容。",
    )


def get_day_file_path(db: Session, *, entry_date: date) -> Path | None:
    day = get_day_by_date(db, entry_date=entry_date)
    if day is None or not day.combined_audio_path:
        return None
    return Path(day.combined_audio_path)


def _get_or_create_day(db: Session, *, entry_date: date, username: str) -> JournalDay:
    day = get_day_by_date(db, entry_date=entry_date)
    if day is None:
        day = create_day(db, entry_date=entry_date, username=username)
    return day


def _resolve_extension(filename: str) -> str:
    settings = get_settings()
    suffix = Path(filename).suffix.lower()
    if not suffix:
        raise JournalServiceError("音频文件缺少扩展名。")
    if suffix.lstrip(".") not in settings.supported_audio_extensions:
        supported = ", ".join(sorted(settings.supported_audio_extensions))
        raise JournalServiceError(f"暂不支持该音频格式，请使用: {supported}")
    return suffix


def _upload_daily_audio(
    day: JournalDay,
    *,
    combined_path: Path,
    entry_date: date,
    warnings: list[str],
) -> None:
    try:
        stored = upload_daily_audio(combined_path, entry_date=entry_date)
    except StorageError as exc:
        day.storage_status = "failed"
        warnings.append(str(exc))
        return

    day.storage_status = "ready"
    day.storage_provider = stored.provider
    day.combined_audio_object_key = stored.key
    day.combined_audio_url = stored.url


def _refresh_transcript(
    day: JournalDay,
    *,
    combined_path: Path,
    entry_date: date,
    warnings: list[str],
) -> None:
    previous_stt = (day.stt_text or "").strip()
    manually_edited = bool(day.entry_text.strip()) and day.entry_text.strip() != previous_stt

    try:
        transcription = transcribe_audio(
            combined_path,
            entry_date=entry_date,
            segment_count=day.segment_count,
        )
    except STTError as exc:
        day.transcript_status = "failed"
        warnings.append(str(exc))
        return

    day.transcript_status = "ready"
    day.last_transcribed_at = datetime.now(UTC)
    day.stt_text = transcription.text
    if not manually_edited:
        day.entry_text = transcription.text
