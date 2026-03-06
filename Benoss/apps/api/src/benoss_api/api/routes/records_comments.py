"""Record comments endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Record, User
from ...repositories.records_repo import list_comments as list_comments_repo
from ...services.records_commands import RecordCommandError, create_comment
from ...services.records_service import comment_payload, is_visible
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/records/{record_id}/comments")
def list_comments(
    record_id: int,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = db.get(Record, record_id)
    if not record or not is_visible(record, user):
        raise HTTPException(status_code=404, detail="not found")
    comments = list_comments_repo(db, record_id=record_id)
    return {"items": [comment_payload(comment) for comment in comments]}


@router.post("/records/{record_id}/comments", status_code=201)
async def create_comment_endpoint(
    record_id: int,
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = db.get(Record, record_id)
    if not record or not is_visible(record, user):
        raise HTTPException(status_code=404, detail="not found")

    body = await request.json()
    try:
        comment = create_comment(db, record_id=record_id, user_id=user.id, body=body.get("body"))
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return comment_payload(comment)
