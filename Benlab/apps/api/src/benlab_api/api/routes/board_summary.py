"""Board summary endpoints."""

from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.board_api_repo import (
    latest_visible_message_day,
    list_heat_rows,
    list_top_tags,
    list_users_by_ids,
)
from ...services.admin_identity import is_admin_member
from ...services.board_views import build_date_range, build_users_heat, clamp_days, day_start, top_tags_payload
from ...utils.runtime_settings import get_setting_int
from ..deps import require_api_user

router = APIRouter(tags=["board"])


@router.get("/board")
def get_board(
    days: int = Query(0),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    days = clamp_days(days, default_days=get_setting_int("BOARD_DEFAULT_DAYS", default=7))

    today = date.today()
    start_date = today - timedelta(days=days - 1)
    date_range = build_date_range(start_date=start_date, days=days)

    is_admin = is_admin_member(user)
    heat_rows = list_heat_rows(db, viewer_user_id=user.id, is_admin=is_admin, start_at=day_start(start_date))
    if not heat_rows:
        latest_day = latest_visible_message_day(db, viewer_user_id=user.id, is_admin=is_admin)
        if latest_day is not None and latest_day < start_date:
            start_date = latest_day - timedelta(days=days - 1)
            date_range = build_date_range(start_date=start_date, days=days)
            heat_rows = list_heat_rows(db, viewer_user_id=user.id, is_admin=is_admin, start_at=day_start(start_date))

    all_user_ids = sorted({int(row.user_id) for row in heat_rows})
    users_map = {u.id: u.username for u in list_users_by_ids(db, user_ids=all_user_ids)}
    users_out = build_users_heat(heat_rows=heat_rows, users_map=users_map, date_range=date_range)

    top_tags_days = get_setting_int("BOARD_TOP_TAGS_DAYS", default=30)
    top_tags_limit = get_setting_int("BOARD_TOP_TAGS_LIMIT", default=10)
    top_tags_start_at = day_start(today - timedelta(days=top_tags_days)) if top_tags_days > 0 else None

    top_tags_rows = list_top_tags(
        db,
        viewer_user_id=user.id,
        is_admin=is_admin,
        limit=top_tags_limit,
        start_at=top_tags_start_at,
    )

    return {
        "dates": date_range,
        "users": users_out,
        "top_tags": top_tags_payload(top_tags_rows),
    }
