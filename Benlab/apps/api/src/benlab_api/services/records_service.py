from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime

from benlab_api.models import Log, Member, Message
from benlab_api.services.admin_identity import is_admin_member

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
        text = str(item or "").strip().lstrip("#")
        if not text or len(text) > 40:
            continue
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


def is_visible(record: Message, user: Member, *, visibility: str = "private") -> bool:
    vis = normalize_visibility(visibility)
    return is_admin_member(user) or user.id in {record.sender_id, record.receiver_id} or vis == "public"


def extract_tags_from_message(record: Message) -> list[str]:
    return auto_tags(record.content)


def _content_payload(
    record: Message,
    *,
    include_text: bool = True,
    include_signed_url: bool = False,  # noqa: ARG001 - API-shape parity
    signed_url_expires: int = 300,  # noqa: ARG001 - API-shape parity
) -> dict:
    text_value = str(record.content or "")
    data = text_value.encode("utf-8")
    payload: dict = {
        "id": record.id,
        "kind": "text",
        "file_type": "text",
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "blob_url": f"/api/contents/{record.id}/blob",
        "signed_url": "",
        "media_type": "text",
    }
    if include_text:
        payload["text"] = text_value
    return payload


def record_payload(
    record: Message,
    *,
    viewer: Member,
    include_content: bool = True,
    include_signed_url: bool = False,
) -> dict:
    visibility = normalize_visibility(getattr(record, "_api_visibility", "private"))
    can_view = is_visible(record, viewer, visibility=visibility)
    return {
        "id": record.id,
        "record_no": record.id,
        "visibility": visibility,
        "tags": extract_tags_from_message(record),
        "preview": preview_text(record.content or ""),
        "created_at": iso_datetime(record.timestamp),
        "updated_at": iso_datetime(record.timestamp),
        "can_edit": viewer.id == record.sender_id,
        "can_clone": can_view,
        "can_comment": can_view,
        "user": {
            "id": record.sender.id if record.sender else record.sender_id,
            "username": record.sender.username if record.sender else "",
        },
        **(
            {"content": _content_payload(record, include_signed_url=include_signed_url)}
            if include_content
            else {}
        ),
    }


def _comment_body(comment: Log) -> str:
    try:
        payload = json.loads(comment.details or "")
    except (TypeError, json.JSONDecodeError):
        return comment.details or ""
    if not isinstance(payload, dict):
        return comment.details or ""
    return str(payload.get("body") or "")


def comment_payload(comment: Log) -> dict:
    return {
        "id": comment.id,
        "body": _comment_body(comment),
        "created_at": iso_datetime(comment.timestamp),
        "updated_at": iso_datetime(comment.timestamp),
        "user": {
            "id": comment.user.id if comment.user else comment.user_id,
            "username": comment.user.username if comment.user else "",
        },
    }
