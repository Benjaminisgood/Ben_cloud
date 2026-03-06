"""Record content blob endpoints."""

import mimetypes

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import get_attachment, get_record_by_content_id, get_record_visibility
from ...services.records_service import is_visible
from ...services.uploads import abs_attachment_path
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.get("/contents/{content_id}/blob")
def get_content_blob(
    content_id: int,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = get_record_by_content_id(db, content_id)
    if record:
        visibility = get_record_visibility(db, record_id=record.id)
        setattr(record, "_api_visibility", visibility)
        if not is_visible(record, user, visibility=visibility):
            raise HTTPException(status_code=404, detail="not found")
        return Response(content=(record.content or "").encode("utf-8"), media_type="text/plain; charset=utf-8")

    attachment = get_attachment(db, content_id)
    if not attachment:
        raise HTTPException(status_code=404, detail="not found")

    path = abs_attachment_path(attachment.filename)
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="blob not found")

    media_type = mimetypes.guess_type(attachment.filename)[0] or "application/octet-stream"
    return FileResponse(path=str(path), media_type=media_type, filename=attachment.filename)
