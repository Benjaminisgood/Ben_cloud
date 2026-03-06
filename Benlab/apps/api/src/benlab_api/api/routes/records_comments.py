"""Record comments endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import get_record_detail, get_record_visibility, list_comments as list_comments_repo
from ...services.records_commands import RecordCommandError, create_comment
from ...services.records_service import comment_payload, is_visible
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/records/{record_id}/comments")
def list_comments(
    record_id: int,
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

    comments = list_comments_repo(db, record_id=record_id)
    return {"items": [comment_payload(comment) for comment in comments]}


@router.post("/records/{record_id}/comments", status_code=201)
async def create_comment_endpoint(
    record_id: int,
    request: Request,
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

    body = await request.json()
    try:
        comment = create_comment(db, record_id=record_id, user_id=user.id, body=body.get("body"))
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return comment_payload(comment)
