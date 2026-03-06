"""Notice render/action endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.notice_repo import list_notice_render_records
from ...services.notice_views import parse_day_filter, parse_user_id_filter, render_notice_html
from ..deps import require_api_user

router = APIRouter(tags=["notice"])


@router.post("/notice/generate")
async def generate_notice(
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    return {"error": "AI generation is handled via /api/digest/daily; this endpoint is reserved"}


@router.get("/notice/render")
def render_notice(
    user_id: str = Query(""),
    tag: str = Query(""),
    day: str = Query(""),
    order: str = Query("desc"),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_start, day_end = parse_day_filter(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    rows = list_notice_render_records(
        db,
        viewer_user_id=user.id,
        user_id=parse_user_id_filter(user_id),
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        order=order,
        limit=100,
    )

    return {
        "rendered_html": render_notice_html(rows, viewer_user_id=user.id),
        "count": len(rows),
    }
