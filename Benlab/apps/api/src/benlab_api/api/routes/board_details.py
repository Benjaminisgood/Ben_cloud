"""Board detail/list endpoints."""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.board_api_repo import list_date_records, list_records_in_user_day, list_user_records
from ...services.admin_identity import is_admin_member
from ...services.board_views import day_start, parse_day, record_item_payload, records_list_payload
from ..deps import require_api_user

router = APIRouter(tags=["board"])


@router.get("/board/cell")
def get_board_cell(
    day: str = Query(...),
    uid: int = Query(...),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_date = parse_day(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    start = day_start(day_date)
    end = start + timedelta(days=1)
    records = list_records_in_user_day(
        db,
        viewer_user_id=user.id,
        is_admin=is_admin_member(user),
        user_id=uid,
        start_at=start,
        end_at=end,
    )
    return {"items": [record_item_payload(record) for record in records]}


@router.get("/board/user/{uid}/records")
def get_user_records(
    uid: int,
    before_id: int = Query(0),
    limit: int = Query(20, ge=1, le=100),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows = list_user_records(
        db,
        viewer_user_id=user.id,
        is_admin=is_admin_member(user),
        user_id=uid,
        before_id=before_id,
        limit=limit,
    )
    return records_list_payload(rows, limit=limit)


@router.get("/board/date/{day}")
def get_date_records(
    day: str,
    before_id: int = Query(0),
    limit: int = Query(40, ge=1, le=200),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    try:
        day_date = parse_day(day)
    except ValueError:
        raise HTTPException(status_code=400, detail="invalid day format")

    start = day_start(day_date)
    end = start + timedelta(days=1)
    rows = list_date_records(
        db,
        viewer_user_id=user.id,
        is_admin=is_admin_member(user),
        start_at=start,
        end_at=end,
        before_id=before_id,
        limit=limit,
    )
    return records_list_payload(rows, limit=limit)
