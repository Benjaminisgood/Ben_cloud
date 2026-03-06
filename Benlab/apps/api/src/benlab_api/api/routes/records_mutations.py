"""Record create/update/delete endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Member
from ...repositories.records_api_repo import get_record_detail
from ...services.records_commands import RecordCommandError, create_record, delete_record, update_record
from ...services.records_service import record_payload
from ..deps import require_api_user

router = APIRouter(tags=["records"])


@router.post("/records", status_code=201)
async def create_record_endpoint(
    request: Request,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    content_type_header = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type_header or "application/x-www-form-urlencoded" in content_type_header:
        form = await request.form()
        text_value = str(form.get("text") or "").strip()
        visibility = form.get("visibility")
        raw_tags = str(form.get("tags") or "")
        receiver_id = form.get("receiver_id")
        upload_file = form.get("file")
    else:
        body = await request.json()
        text_value = str(body.get("text") or "").strip()
        visibility = body.get("visibility")
        raw_tags = body.get("tags") or ""
        receiver_id = body.get("receiver_id")
        upload_file = None

    try:
        record = create_record(
            db,
            user=user,
            text_value=text_value,
            visibility=visibility,
            raw_tags=raw_tags,
            upload_file=upload_file,
            receiver_id=receiver_id,
        )
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return record_payload(record, viewer=user, include_content=True)


@router.patch("/records/{record_id}")
async def update_record_endpoint(
    record_id: int,
    request: Request,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = get_record_detail(db, record_id)
    if not record or record.sender_id != user.id:
        raise HTTPException(status_code=404, detail="not found")

    body = await request.json()
    try:
        updated = update_record(db, record=record, body=body)
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return record_payload(updated, viewer=user, include_content=True)


@router.delete("/records/{record_id}", status_code=204)
def delete_record_endpoint(
    record_id: int,
    user: Member = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = get_record_detail(db, record_id)
    if not record or record.sender_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    delete_record(db, record=record)
