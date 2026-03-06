"""Record listing and detail endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import (
    get_record_detail,
    get_record_visibility,
    list_records as list_records_repo,
    pull_records as pull_records_repo,
)
from ...services.admin_identity import is_admin_member
from ...services.records_service import is_visible, record_payload
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
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    items, has_more = list_records_repo(
        db,
        viewer_id=user.id,
        is_admin=is_admin_member(user),
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
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    rows, has_more = pull_records_repo(
        db,
        viewer_id=user.id,
        is_admin=is_admin_member(user),
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
    include_signed_url: bool = Query(False),
    signed_url_expires: int = Query(300),
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = get_record_detail(db, record_id)
    if not record:
        raise HTTPException(status_code=404, detail="not found")

    visibility = get_record_visibility(db, record_id=record.id)
    setattr(record, "_api_visibility", visibility)
    if not is_visible(record, user, visibility=visibility):
        raise HTTPException(status_code=404, detail="not found")
    return record_payload(record, viewer=user, include_content=True, include_signed_url=include_signed_url)
