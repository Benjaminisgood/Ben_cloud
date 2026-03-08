from __future__ import annotations

import json
from datetime import date
from mimetypes import guess_type

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session

from benjournal_api.db.session import get_db
from benjournal_api.services.journal_dashboard import build_dashboard_snapshot
from benjournal_api.services.journal_days import get_day_file_path

from ..deps import get_session_user
from ..templating import render_template

router = APIRouter(tags=["pages"])


@router.get("/", response_class=HTMLResponse)
def journal_home(
    request: Request,
    selected_date: date | None = Query(default=None, alias="date"),
    db: Session = Depends(get_db),
):
    user = get_session_user(request)
    if not user:
        return RedirectResponse("/login", status_code=303)

    snapshot = build_dashboard_snapshot(db, selected_date=selected_date)
    snapshot_payload = snapshot.model_dump(mode="json")
    return render_template(
        request,
        "journal.html",
        {
            "title": "Benjournal",
            "current_user": user,
            "snapshot": snapshot_payload,
            "snapshot_json": json.dumps(snapshot_payload, ensure_ascii=False),
            "theme": {
                "primary": "#6c2f1f",
                "secondary": "#d28558",
                "canvas": "#f7efe3",
                "ink": "#23160f",
            },
        },
    )


@router.get("/portal")
def portal() -> RedirectResponse:
    return RedirectResponse("/", status_code=303)


@router.get("/journal-days/{entry_date}/audio")
def download_combined_audio(
    entry_date: date,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="auth_required")

    audio_path = get_day_file_path(db, entry_date=entry_date)
    if audio_path is None or not audio_path.exists():
        raise HTTPException(status_code=404, detail="combined_audio_not_found")

    content_type = guess_type(audio_path.name)[0] or "application/octet-stream"
    return FileResponse(audio_path, media_type=content_type, filename=audio_path.name)
