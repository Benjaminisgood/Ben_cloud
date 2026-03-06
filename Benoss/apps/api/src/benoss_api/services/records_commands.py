from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from fastapi import UploadFile
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.orm import Session
from werkzeug.utils import secure_filename

from ..core.config import get_settings
from ..models import Comment, Content, Record, User
from ..services.records_service import (
    apply_tags,
    auto_tags,
    cleanup_orphan_tags,
    normalize_visibility,
    parse_tags,
    preview_text,
)
from ..utils.file_types import detect_file_type
from ..utils.ids import new_uuid
from ..utils.oss import (
    copy_object,
    has_remote_backend,
    object_exists,
    put_object_bytes,
    put_object_from_file,
    sign_put_url,
)
from ..utils.oss_paths import record_content_key

DIRECT_UPLOAD_TOKEN_SALT = "benoss.direct-upload.v1"


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


def _direct_upload_serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().SECRET_KEY, salt=DIRECT_UPLOAD_TOKEN_SALT)


def text_to_content(text_value: str) -> Content:
    text = str(text_value or "")
    data = text.encode("utf-8")
    object_id = new_uuid()
    oss_key = record_content_key(object_id, "text.txt")
    put_object_bytes(oss_key, data, content_type="text/plain; charset=utf-8")
    return Content(
        kind="text",
        file_type="text",
        text_content=preview_text(text, limit=2000),
        oss_key=oss_key,
        filename="text.txt",
        content_type="text/plain; charset=utf-8",
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def file_to_content(upload: UploadFile) -> tuple[Content, str]:
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_TMP_DIR)
    upload_dir.mkdir(parents=True, exist_ok=True)

    filename = secure_filename(upload.filename or "") or f"upload-{new_uuid()}"
    suffix = Path(filename).suffix
    tmp_path = upload_dir / f"{new_uuid()}{suffix}"

    data = upload.file.read()
    tmp_path.write_bytes(data)

    try:
        size_bytes = len(data)
        sha256 = hashlib.sha256(data).hexdigest()
        content_type = upload.content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream"
        content_type = content_type.split(";")[0].strip()
        file_type = detect_file_type(content_type, filename)
        object_id = new_uuid()
        oss_key = record_content_key(object_id, filename)
        put_object_from_file(oss_key, str(tmp_path), content_type=content_type)
        content = Content(
            kind="file",
            file_type=file_type,
            oss_key=oss_key,
            filename=filename,
            content_type=content_type,
            size_bytes=size_bytes,
            sha256=sha256,
        )
        return content, filename
    finally:
        tmp_path.unlink(missing_ok=True)


def create_record(
    db: Session,
    *,
    user: User,
    text_value: str,
    visibility,
    raw_tags,
    upload_file,
) -> Record:
    text_value = str(text_value or "").strip()
    visibility_value = normalize_visibility(visibility)
    tags = resolve_tags(raw_tags, text_value)

    if upload_file and hasattr(upload_file, "filename") and upload_file.filename:
        content, _ = file_to_content(upload_file)
    elif text_value:
        content = text_to_content(text_value)
    else:
        raise RecordCommandError("text or file is required")

    db.add(content)
    db.flush()

    record = Record(
        user_id=user.id,
        content_id=content.id,
        visibility=visibility_value,
        preview=preview_text(text_value or content.filename or ""),
    )
    db.add(record)
    db.flush()
    apply_tags(db, record, tags)
    db.commit()
    db.refresh(record)
    return record


def _replace_record_content(target: Content, source: Content) -> None:
    target.kind = source.kind
    target.file_type = source.file_type
    target.text_content = source.text_content
    target.oss_key = source.oss_key
    target.filename = source.filename
    target.content_type = source.content_type
    target.size_bytes = int(source.size_bytes or 0)
    target.sha256 = source.sha256 or ""


def _replace_record_content_from_upload(record: Record, upload_file: UploadFile) -> None:
    content, filename = file_to_content(upload_file)
    if not record.content:
        raise RecordCommandError("record content not found")
    _replace_record_content(record.content, content)
    record.preview = preview_text(filename or record.content.filename or "")


def _replace_record_content_from_direct_upload(record: Record, *, token: str) -> None:
    if not record.content:
        raise RecordCommandError("record content not found")

    parsed = _parse_direct_upload_token(token=token, user_id=record.user_id)
    oss_key = str(parsed.get("oss_key") or "")
    if not object_exists(oss_key):
        raise RecordCommandError("file not found, please upload first")

    filename = str(parsed.get("filename") or "")
    content_type = str(parsed.get("content_type") or "")
    size_bytes = int(parsed.get("size_bytes") or 0)
    sha256_value = str(parsed.get("sha256") or "")

    content = Content(
        kind="file",
        file_type=detect_file_type(content_type, filename),
        text_content="",
        oss_key=oss_key,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256_value,
    )
    _replace_record_content(record.content, content)
    record.preview = preview_text(filename or record.content.filename or "")


def update_record(
    db: Session,
    *,
    record: Record,
    body: dict,
    upload_file: UploadFile | None = None,
) -> Record:
    if "visibility" in body:
        record.visibility = normalize_visibility(body["visibility"], default=record.visibility)
    if "tags" in body:
        apply_tags(db, record, parse_tags(body["tags"]))
        cleanup_orphan_tags(db)

    if "text" in body:
        if not record.content or record.content.kind != "text":
            raise RecordCommandError("text updates are only supported for text records")
        new_text = str(body["text"] or "").strip()
        if not new_text:
            raise RecordCommandError("text is required")
        data = new_text.encode("utf-8")
        put_object_bytes(record.content.oss_key, data, content_type="text/plain; charset=utf-8")
        record.content.text_content = preview_text(new_text, limit=2000)
        record.content.size_bytes = len(data)
        record.content.sha256 = hashlib.sha256(data).hexdigest()
        record.preview = preview_text(new_text)

    uploaded_file_token = str(body.get("uploaded_file_token") or "").strip()
    if uploaded_file_token:
        _replace_record_content_from_direct_upload(record, token=uploaded_file_token)
    elif upload_file and getattr(upload_file, "filename", ""):
        _replace_record_content_from_upload(record, upload_file)

    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, *, record: Record) -> None:
    db.delete(record)
    cleanup_orphan_tags(db)
    db.commit()


def clone_record(
    db: Session,
    *,
    source_record: Record,
    user: User,
    visibility=None,
) -> Record:
    source_content = source_record.content
    if not source_content:
        raise RecordCommandError("source content not found")

    source_tags = source_record.get_tags()
    default_visibility = "private" if source_record.user_id != user.id else source_record.visibility
    visibility_value = normalize_visibility(visibility, default=default_visibility)

    if source_content.kind == "text" and not source_content.oss_key:
        cloned_content = text_to_content(source_content.text_content or source_record.preview or "")
    else:
        source_oss_key = str(source_content.oss_key or "").strip()
        if not source_oss_key:
            raise RecordCommandError("source file missing")
        source_filename = source_content.filename or ("text.txt" if source_content.kind == "text" else f"file-{new_uuid()}")
        target_oss_key = record_content_key(new_uuid(), source_filename)
        try:
            copy_object(source_oss_key, target_oss_key)
        except Exception as exc:
            raise RecordCommandError("clone content failed") from exc
        cloned_content = Content(
            kind=source_content.kind,
            file_type=source_content.file_type,
            text_content=source_content.text_content or "",
            oss_key=target_oss_key,
            filename=source_content.filename or "",
            content_type=source_content.content_type or "",
            size_bytes=int(source_content.size_bytes or 0),
            sha256=source_content.sha256 or "",
        )

    db.add(cloned_content)
    db.flush()

    cloned_record = Record(
        user_id=user.id,
        content_id=cloned_content.id,
        visibility=visibility_value,
        preview=source_record.preview or "",
    )
    db.add(cloned_record)
    db.flush()
    apply_tags(db, cloned_record, source_tags)
    db.commit()
    db.refresh(cloned_record)
    return cloned_record


def create_comment(
    db: Session,
    *,
    record_id: int,
    user_id: int,
    body,
) -> Comment:
    comment_body = validate_comment_body(body)
    comment = Comment(record_id=record_id, user_id=user_id, body=comment_body)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def issue_direct_upload_token(
    *,
    user: User,
    filename: str,
    content_type: str,
    size_bytes: int,
    sha256: str,
) -> dict:
    settings = get_settings()
    if not has_remote_backend():
        raise RecordCommandError("direct upload not available")

    safe_filename = secure_filename(filename) or f"upload-{new_uuid()}"
    content_type_value = content_type.split(";")[0].strip() or mimetypes.guess_type(safe_filename)[0] or "application/octet-stream"
    object_id = new_uuid()
    oss_key = record_content_key(object_id, safe_filename)
    put_url = sign_put_url(oss_key, expires=settings.OSS_DIRECT_UPLOAD_EXPIRES_SECONDS, content_type=content_type_value)

    payload = {
        "v": 1,
        "user_id": user.id,
        "oss_key": oss_key,
        "filename": safe_filename,
        "content_type": content_type_value,
        "size_bytes": size_bytes,
    }
    if sha256:
        payload["sha256"] = sha256

    token = _direct_upload_serializer().dumps(payload)
    return {"token": token, "put_url": put_url, "oss_key": oss_key}


def _parse_direct_upload_token(*, token: str, user_id: int) -> dict:
    max_age = get_settings().OSS_DIRECT_UPLOAD_TOKEN_MAX_AGE_SECONDS
    try:
        parsed = _direct_upload_serializer().loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        raise RecordCommandError("invalid or expired token")

    if int(parsed.get("user_id") or 0) != user_id:
        raise RecordCommandError("token mismatch")
    return parsed


def confirm_direct_upload(
    db: Session,
    *,
    user: User,
    token: str,
    visibility,
    raw_tags,
) -> Record:
    parsed = _parse_direct_upload_token(token=token, user_id=user.id)

    oss_key = str(parsed.get("oss_key") or "")
    if not object_exists(oss_key):
        raise RecordCommandError("file not found, please upload first")

    filename = str(parsed.get("filename") or "")
    content_type = str(parsed.get("content_type") or "")
    size_bytes = int(parsed.get("size_bytes") or 0)
    sha256_value = str(parsed.get("sha256") or "")

    content = Content(
        kind="file",
        file_type=detect_file_type(content_type, filename),
        oss_key=oss_key,
        filename=filename,
        content_type=content_type,
        size_bytes=size_bytes,
        sha256=sha256_value,
    )
    db.add(content)
    db.flush()

    record = Record(
        user_id=user.id,
        content_id=content.id,
        visibility=normalize_visibility(visibility),
        preview=preview_text(filename),
    )
    db.add(record)
    db.flush()
    apply_tags(db, record, parse_tags(raw_tags))
    db.commit()
    db.refresh(record)
    return record
