"""Notice query endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import list_notice_records
from ...services.admin_identity import is_admin_member
from ...services.notice_views import parse_day_filter, parse_user_id_filter, records_response
from ..deps import require_api_user

router = APIRouter(tags=["notice"])


@router.get("/notice/records")
def get_notice_records(
    user_id: str = Query(""),
    tag: str = Query(""),
    day: str = Query(""),
    before_id: Optional[int] = Query(None),
    limit: int = Query(200, ge=1, le=1000),
    text_source: str = Query("oss"),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_start, day_end = parse_day_filter(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    rows = list_notice_records(
        db,
        viewer_id=user.id,
        is_admin=is_admin_member(user),
        user_id=parse_user_id_filter(user_id),
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=before_id,
        limit=limit,
    )
    return records_response(rows, limit=limit, text_source=text_source)
