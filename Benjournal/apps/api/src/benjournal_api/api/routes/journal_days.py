from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from benjournal_api.api.deps import require_user
from benjournal_api.db.session import get_db
from benjournal_api.schemas.journal_day import (
    JournalDayListItem,
    JournalDayRead,
    JournalIngestResponse,
    JournalTextUpdate,
)
from benjournal_api.services.journal_days import (
    JournalServiceError,
    get_journal_day_detail,
    ingest_audio_segment,
    list_recent_journal_days,
    update_journal_text,
)

router = APIRouter(tags=["journal_days"])


@router.get("/journal-days", response_model=list[JournalDayListItem])
def get_journal_days(
    limit: int = 14,
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> list[JournalDayListItem]:
    return list_recent_journal_days(db, limit=limit)


@router.get("/journal-days/{entry_date}", response_model=JournalDayRead)
def get_journal_day(
    entry_date: date,
    _: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> JournalDayRead:
    day = get_journal_day_detail(db, entry_date=entry_date)
    if day is None:
        raise HTTPException(status_code=404, detail="journal_day_not_found")
    return day


@router.post(
    "/journal-days/{entry_date}/segments",
    response_model=JournalIngestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_journal_segment(
    entry_date: date,
    audio_file: UploadFile = File(...),
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> JournalIngestResponse:
    try:
        payload = await audio_file.read()
        return ingest_audio_segment(
            db,
            entry_date=entry_date,
            audio_bytes=payload,
            filename=audio_file.filename or "journal-audio.wav",
            content_type=audio_file.content_type or "application/octet-stream",
            username=user["username"],
        )
    except JournalServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.patch("/journal-days/{entry_date}", response_model=JournalDayRead)
def patch_journal_day(
    entry_date: date,
    payload: JournalTextUpdate,
    user: dict[str, str] = Depends(require_user),
    db: Session = Depends(get_db),
) -> JournalDayRead:
    return update_journal_text(
        db,
        entry_date=entry_date,
        entry_text=payload.entry_text,
        username=user["username"],
    )
