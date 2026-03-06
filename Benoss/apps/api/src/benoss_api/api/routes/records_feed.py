"""Record listing and detail endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.records_repo import (
    get_record_detail,
    list_comments as list_comments_repo,
    list_records as list_records_repo,
    pull_records as pull_records_repo,
)
from ...services.records_service import comment_payload, is_visible, record_payload
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/records")
def list_records(
    user_id: str = Query(""),
    tag: str = Query(""),
    day: str = Query(""),
    visibility: str = Query(""),
    before_id: Optional[int] = Query(None),
    limit: int = Query(40, ge=1, le=200),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    items, has_more = list_records_repo(
        db,
        viewer_id=user.id,
        user_id=int(user_id) if user_id and user_id.isdigit() else None,
        tag=tag,
        day=day,
        visibility=visibility,
        before_id=before_id,
        limit=limit,
    )
    return {
        "items": [record_payload(record, viewer=user, include_content=True) for record in items],
        "has_more": has_more,
    }


@router.get("/pull")
def pull_records(
    user_id: str = Query(""),
    tag: str = Query(""),
    day: str = Query(""),
    before_id: Optional[int] = Query(None),
    limit: int = Query(40, ge=1, le=200),
    text_source: str = Query("oss"),
    include_signed_url: bool = Query(False),
    signed_url_expires: int = Query(300),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows, has_more = pull_records_repo(
        db,
        viewer_id=user.id,
        user_id=int(user_id) if user_id and user_id.isdigit() else None,
        tag=tag,
        before_id=before_id,
        limit=limit,
    )
    return {
        "items": [
            record_payload(record, viewer=user, include_content=True, include_signed_url=include_signed_url)
            for record in rows
        ],
        "has_more": has_more,
    }


@router.get("/records/{record_id}")
def get_record(
    record_id: int,
    include_comments: bool = Query(False),
    include_signed_url: bool = Query(False),
    signed_url_expires: int = Query(300),
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = get_record_detail(db, record_id)
    if not record or not is_visible(record, user):
        raise HTTPException(status_code=404, detail="not found")
    payload = record_payload(record, viewer=user, include_content=True, include_signed_url=include_signed_url)
    if include_comments:
        comments = list_comments_repo(db, record_id=record_id)
        payload["comments"] = [comment_payload(comment) for comment in comments]
    return payload
