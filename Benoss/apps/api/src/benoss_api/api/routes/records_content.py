"""Record content blob endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import User
from ...repositories.records_repo import get_content, get_record_by_content_id
from ...services.records_service import is_visible
from ...utils.oss import get_object_bytes
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/contents/{content_id}/blob")
def get_content_blob(
    content_id: int,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    content = get_content(db, content_id)
    if not content:
        raise HTTPException(status_code=404, detail="not found")
    record = get_record_by_content_id(db, content_id)
    if not record or not is_visible(record, user):
        raise HTTPException(status_code=404, detail="not found")
    try:
        data = get_object_bytes(content.oss_key)
    except Exception:
        raise HTTPException(status_code=404, detail="blob not found")
    return Response(content=data, media_type=content.content_type or "application/octet-stream")
