"""Echoes – mixed record + generated-asset stream."""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.echoes_repo import list_echo_assets, list_echo_records
from ...services.echoes_views import VALID_FILE_TYPES, build_echoes_response
from ..deps import require_api_user

router = APIRouter(tags=["echoes"])

VALID_ECHOES_SCOPES = {"public", "with_mine"}
VALID_CURSOR_KINDS = {"", "record", "asset"}


def _parse_cursor_time(value: str) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="invalid cursor_time format") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
    return parsed


@router.get("/echoes")
def get_echoes(
    scope: str = Query("with_mine"),
    file_type: str = Query(""),
    cursor_time: str = Query(""),
    cursor_kind: str = Query(""),
    cursor_id: Optional[int] = Query(None, ge=1),
    before_id: Optional[int] = Query(None, ge=1),
    before_asset_id: Optional[int] = Query(None, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    if file_type and file_type not in VALID_FILE_TYPES:
        raise HTTPException(status_code=400, detail="invalid file_type")
    if scope not in VALID_ECHOES_SCOPES:
        raise HTTPException(status_code=400, detail="invalid scope")
    if cursor_kind not in VALID_CURSOR_KINDS:
        raise HTTPException(status_code=400, detail="invalid cursor_kind")

    parsed_cursor_time = _parse_cursor_time(cursor_time)
    parsed_cursor_kind = cursor_kind
    parsed_cursor_id = cursor_id
    if parsed_cursor_time is None:
        # Backward compatibility with older pagination params.
        if before_id:
            parsed_cursor_kind = "record"
            parsed_cursor_id = before_id
        elif before_asset_id:
            parsed_cursor_kind = "asset"
            parsed_cursor_id = before_asset_id

    include_private = scope == "with_mine"
    records = list_echo_records(
        db,
        viewer_user_id=user.id,
        include_private=include_private,
        cursor_time=parsed_cursor_time,
        cursor_id=parsed_cursor_id,
        cursor_kind=parsed_cursor_kind,
        limit=limit,
    )
    assets = list_echo_assets(
        db,
        viewer_user_id=user.id,
        include_private=include_private,
        cursor_time=parsed_cursor_time,
        cursor_id=parsed_cursor_id,
        cursor_kind=parsed_cursor_kind,
        limit=limit,
    )

    return build_echoes_response(
        records=records,
        assets=assets,
        viewer=user,
        file_type=file_type,
        scope=scope,
        limit=limit,
    )
