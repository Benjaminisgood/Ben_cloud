from __future__ import annotations

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session

from benlab_api.core.config import get_settings
from benlab_api.models import Member, Message
from benlab_api.repositories.records_api_repo import (
    create_comment as create_comment_repo,
    create_record as create_record_repo,
    delete_record as delete_record_repo,
    set_record_visibility,
    update_record as update_record_repo,
)
from benlab_api.services.records_service import auto_tags, normalize_visibility, parse_tags

DIRECT_UPLOAD_TOKEN_SALT = "benlab.direct-upload.v1"


class RecordCommandError(ValueError):
    pass


def resolve_tags(raw_tags, text_value: str) -> list[str]:
    tags = parse_tags(raw_tags)
    if not tags and text_value:
        tags = auto_tags(text_value)
    return tags


def validate_comment_body(raw_body) -> str:
    comment_body = str(raw_body or "").strip()
    if not comment_body:
        raise RecordCommandError("body is required")
    if len(comment_body) > 2000:
        raise RecordCommandError("body too long")
    return comment_body


def _merge_content_with_tags(text_value: str, tags: list[str]) -> str:
    base = str(text_value or "").strip()
    if not tags:
        return base
    existing = {tag.lower() for tag in auto_tags(base)}
    extra = [f"#{tag}" for tag in tags if tag.lower() not in existing]
    if not extra:
        return base
    if not base:
        return " ".join(extra)
    return f"{base}\n\n{' '.join(extra)}"


def _resolve_receiver_id(db: Session, *, user: Member, receiver_id) -> int:
    token = str(receiver_id or "").strip()
    if not token:
        return user.id
    if not token.isdigit():
        raise RecordCommandError("receiver_id must be integer")
    parsed = int(token)
    target = db.get(Member, parsed)
    if not target:
        raise RecordCommandError("receiver not found")
    return target.id


def create_record(
    db: Session,
    *,
    user: Member,
    text_value: str,
    visibility,
    raw_tags,
    upload_file,
    receiver_id=None,
) -> Message:
    text_value = str(text_value or "").strip()
    visibility_value = normalize_visibility(visibility)

    if upload_file and getattr(upload_file, "filename", "") and not text_value:
        text_value = f"[file] {upload_file.filename}"

    if not text_value:
        raise RecordCommandError("text or file is required")

    tags = resolve_tags(raw_tags, text_value)
    content = _merge_content_with_tags(text_value, tags)
    record = create_record_repo(
        db,
        sender_id=user.id,
        receiver_id=_resolve_receiver_id(db, user=user, receiver_id=receiver_id),
        content=content,
    )
    set_record_visibility(db, record_id=record.id, visibility=visibility_value, user_id=user.id)
    setattr(record, "_api_visibility", visibility_value)
    return record


def update_record(
    db: Session,
    *,
    record: Message,
    body: dict,
) -> Message:
    text_value = str(body.get("text", record.content) or "").strip()
    if not text_value:
        raise RecordCommandError("text is required")

    if "tags" in body:
        tags = parse_tags(body.get("tags"))
    else:
        tags = auto_tags(text_value)

    content = _merge_content_with_tags(text_value, tags)
    updated = update_record_repo(db, record=record, content=content)

    if "visibility" in body:
        visibility_value = normalize_visibility(body.get("visibility"))
        set_record_visibility(db, record_id=updated.id, visibility=visibility_value, user_id=record.sender_id)
        setattr(updated, "_api_visibility", visibility_value)
    return updated


def delete_record(db: Session, *, record: Message) -> None:
    delete_record_repo(db, record=record)


def create_comment(
    db: Session,
    *,
    record_id: int,
    user_id: int,
    body,
):
    comment_body = validate_comment_body(body)
    return create_comment_repo(db, record_id=record_id, user_id=user_id, body=comment_body)


def _direct_upload_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().SECRET_KEY, salt=DIRECT_UPLOAD_TOKEN_SALT)


def issue_direct_upload_token(
    *,
    user: Member,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
) -> dict:
    payload = {
        "v": 1,
        "user_id": user.id,
        "filename": str(filename or "upload.bin"),
        "content_type": str(content_type or "application/octet-stream"),
        "size_bytes": int(size_bytes or 0),
        "sha256": str(sha256 or ""),
    }
    token = _direct_upload_serializer().dumps(payload)
    return {"token": token, "put_url": "", "oss_key": ""}


def _parse_direct_upload_token(*, token: str, user_id: int) -> dict:
    try:
        parsed = _direct_upload_serializer().loads(token, max_age=3600)
    except (BadSignature, SignatureExpired):
        raise RecordCommandError("invalid or expired token")

    if int(parsed.get("user_id") or 0) != user_id:
        raise RecordCommandError("token mismatch")
    return parsed


def confirm_direct_upload(
    db: Session,
    *,
    user: Member,
    token: str,
    visibility,
    raw_tags,
) -> Message:
    parsed = _parse_direct_upload_token(token=token, user_id=user.id)
    filename = str(parsed.get("filename") or "upload.bin")
    visibility_value = normalize_visibility(visibility)
    text_value = f"[upload] {filename}"
    content = _merge_content_with_tags(text_value, parse_tags(raw_tags))
    record = create_record_repo(db, sender_id=user.id, receiver_id=user.id, content=content)
    set_record_visibility(db, record_id=record.id, visibility=visibility_value, user_id=user.id)
    setattr(record, "_api_visibility", visibility_value)
    return record
