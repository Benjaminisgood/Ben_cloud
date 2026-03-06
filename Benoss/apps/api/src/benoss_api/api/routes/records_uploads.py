"""Record direct-upload endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...services.records_commands import (
    RecordCommandError,
    confirm_direct_upload,
    issue_direct_upload_token,
)
from ...services.records_service import record_payload
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/direct-upload/token")
def get_direct_upload_token(
    filename: str = Query(...),
    content_type: str = Query(""),
    size_bytes: int = Query(0),
    sha256: str = Query(""),
    user: User = Depends(require_api_user),
):
    try:
        return issue_direct_upload_token(
            user=user,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
        )
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/direct-upload/confirm", status_code=201)
async def confirm_direct_upload_endpoint(
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    body = await request.json()
    try:
        record = confirm_direct_upload(
            db,
            user=user,
            token=str(body.get("token") or "").strip(),
            visibility=body.get("visibility"),
            raw_tags=body.get("tags") or "",
        )
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return record_payload(record, viewer=user, include_content=True)
