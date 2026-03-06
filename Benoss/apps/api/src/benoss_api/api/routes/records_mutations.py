"""Record create/update/delete endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...db.session import get_db
from ...models import Record, User
from ...services.records_commands import RecordCommandError, clone_record, create_record, delete_record, update_record
from ...services.records_service import is_visible, record_payload
from ..deps import require_api_user

router = APIRouter(tags=["records"])


async def _parse_record_update_request(request: Request) -> tuple[dict, object | None]:
    content_type_header = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type_header or "application/x-www-form-urlencoded" in content_type_header:
        form = await request.form()
        body: dict[str, object] = {}

        if "visibility" in form:
            body["visibility"] = form.get("visibility")
        if "tags" in form:
            body["tags"] = form.get("tags") or ""
        if "text" in form:
            body["text"] = str(form.get("text") or "")

        uploaded_file_token = str(form.get("uploaded_file_token") or "").strip()
        if uploaded_file_token:
            body["uploaded_file_token"] = uploaded_file_token

        return body, form.get("file")

    try:
        body = await request.json()
    except Exception:
        body = {}
    return body if isinstance(body, dict) else {}, None


@router.post("/records", status_code=201)
async def create_record_endpoint(
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    content_type_header = request.headers.get("content-type", "")
    if "multipart/form-data" in content_type_header or "application/x-www-form-urlencoded" in content_type_header:
        form = await request.form()
        text_value = str(form.get("text") or "").strip()
        visibility = form.get("visibility")
        raw_tags = str(form.get("tags") or "")
        upload_file = form.get("file")
    else:
        body = await request.json()
        text_value = str(body.get("text") or "").strip()
        visibility = body.get("visibility")
        raw_tags = body.get("tags") or ""
        upload_file = None

    try:
        record = create_record(
            db,
            user=user,
            text_value=text_value,
            visibility=visibility,
            raw_tags=raw_tags,
            upload_file=upload_file,
        )
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return record_payload(record, viewer=user, include_content=True)


@router.patch("/records/{record_id}")
async def update_record_endpoint(
    record_id: int,
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = db.get(Record, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")

    body, upload_file = await _parse_record_update_request(request)
    try:
        updated = update_record(db, record=record, body=body, upload_file=upload_file)
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return record_payload(updated, viewer=user, include_content=True)


@router.delete("/records/{record_id}", status_code=204)
def delete_record_endpoint(
    record_id: int,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    record = db.get(Record, record_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="not found")
    delete_record(db, record=record)


@router.post("/records/{record_id}/clone", status_code=201)
async def clone_record_endpoint(
    record_id: int,
    request: Request,
    user: User = Depends(require_api_user),
    db: Session = Depends(get_db),
):
    source_record = db.get(Record, record_id)
    if not source_record or not is_visible(source_record, user):
        raise HTTPException(status_code=404, detail="not found")

    try:
        body = await request.json()
    except Exception:
        body = {}
    try:
        cloned = clone_record(
            db,
            source_record=source_record,
            user=user,
            visibility=body.get("visibility"),
        )
    except RecordCommandError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    return {"record": record_payload(cloned, viewer=user, include_content=True)}
