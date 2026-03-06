from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..models import Comment, Content, Record, Tag, User, _clean_tag_names
from ..utils.file_types import detect_file_type
from ..utils.oss import sign_get_url

VALID_VISIBILITY = {"public", "private"}
_AUTO_TAG_PATTERN = re.compile(r"(?:^|[^0-9A-Za-z_:/#])#([0-9A-Za-z_\-\u3400-\u9fff]{1,40})")


def iso_datetime(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def preview_text(value: str, *, limit: int = 220) -> str:
    text = " ".join((value or "").split())
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def parse_tags(raw) -> list[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        items = raw
    else:
        text = str(raw or "")
        items = [p.strip() for p in text.split(",")]
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or len(text) > 40:
            continue
        text = text[:40]
        low = text.lower()
        if low in seen:
            continue
        seen.add(low)
        result.append(text)
        if len(result) >= 20:
            break
    return result


def auto_tags(raw: str) -> list[str]:
    items = [m.group(1) for m in _AUTO_TAG_PATTERN.finditer(str(raw or ""))]
    return parse_tags(items[:60])


def normalize_visibility(raw, *, default: str = "private") -> str:
    val = str(raw or "").strip().lower() or default
    return val if val in VALID_VISIBILITY else default


def visible_filter(user_id: int, *, public_only: bool = False):
    if public_only:
        return Record.visibility == "public"
    return or_(Record.visibility == "public", Record.user_id == user_id)


def is_visible(record: Record, user: User) -> bool:
    return record.visibility == "public" or record.user_id == user.id


def _content_media_type(content: Content) -> str:
    ft = detect_file_type(content.content_type, content.filename)
    if ft in {"image", "video", "audio", "text"}:
        return ft
    if ft in {"web", "log"}:
        return "text"
    return "file"


def _content_payload(
    content: Content,
    *,
    include_text: bool = True,
    include_signed_url: bool = False,
    signed_url_expires: int = 300,
) -> dict:
    ft = detect_file_type(content.content_type, content.filename) if content.kind == "file" else "text"
    signed_url = ""
    if include_signed_url and content.oss_key:
        try:
            signed_url = sign_get_url(content.oss_key, expires=signed_url_expires) or ""
        except Exception:
            pass

    payload: dict = {
        "id": content.id,
        "kind": content.kind,
        "file_type": ft,
        "size_bytes": int(content.size_bytes or 0),
        "sha256": content.sha256 or "",
        "blob_url": f"/api/contents/{content.id}/blob",
        "signed_url": signed_url,
    }
    if content.kind == "text":
        payload["text"] = str(content.text_content or "") if include_text else ""
        payload["media_type"] = "text"
    else:
        payload["filename"] = content.filename or ""
        payload["content_type"] = content.content_type or ""
        payload["media_type"] = _content_media_type(content)
    return payload


def record_payload(
    record: Record,
    *,
    viewer: User,
    include_content: bool = True,
    include_signed_url: bool = False,
) -> dict:
    return {
        "id": record.id,
        "record_no": record.id,
        "visibility": record.visibility,
        "tags": record.get_tags(),
        "preview": record.preview or "",
        "created_at": iso_datetime(record.created_at),
        "updated_at": iso_datetime(record.updated_at),
        "can_edit": viewer.id == record.user_id,
        "can_clone": is_visible(record, viewer),
        "can_comment": is_visible(record, viewer),
        "user": {
            "id": record.user.id if record.user else record.user_id,
            "username": record.user.username if record.user else "",
        },
        **({"content": _content_payload(record.content, include_signed_url=include_signed_url)} if include_content and record.content else {}),
    }


def comment_payload(comment: Comment) -> dict:
    return {
        "id": comment.id,
        "body": comment.body,
        "created_at": iso_datetime(comment.created_at),
        "updated_at": iso_datetime(comment.updated_at),
        "user": {
            "id": comment.user.id if comment.user else comment.user_id,
            "username": comment.user.username if comment.user else "",
        },
    }


def apply_tags(db: Session, record: Record, tags: list[str]) -> None:
    cleaned = _clean_tag_names(tags)
    if not cleaned:
        record.tags = []
        return
    normalized = [t.lower() for t in cleaned]
    existing = db.query(Tag).filter(Tag.name_norm.in_(normalized)).all()
    existing_map = {t.name_norm: t for t in existing}
    next_tags = []
    for text in cleaned:
        norm = text.lower()
        tag = existing_map.get(norm)
        if tag is None:
            tag = Tag(name=text, name_norm=norm)
            db.add(tag)
            existing_map[norm] = tag
        next_tags.append(tag)
    record.tags = next_tags


def cleanup_orphan_tags(db: Session) -> None:
    db.query(Tag).filter(~Tag.records.any()).delete(synchronize_session=False)

