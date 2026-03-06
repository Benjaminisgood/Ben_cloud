from __future__ import annotations

from datetime import datetime, timedelta
from html import escape

from benlab_api.models import Message
from benlab_api.services.records_service import extract_tags_from_message, normalize_visibility, preview_text


def parse_user_id_filter(user_id: str) -> int | None:
    return int(user_id) if user_id and user_id.isdigit() else None


def parse_day_filter(day: str) -> tuple[datetime | None, datetime | None]:
    if not day:
        return None, None
    start = datetime.strptime(day, "%Y-%m-%d")
    return start, start + timedelta(days=1)


def content_payload(record: Message | None, *, text_source: str) -> dict | None:  # noqa: ARG001 - parity
    if record is None:
        return None
    text_value = str(record.content or "")
    return {
        "kind": "text",
        "text": text_value,
        "size_bytes": len(text_value.encode("utf-8")),
        "blob_url": f"/api/contents/{record.id}/blob",
    }


def record_payload(record: Message, *, text_source: str) -> dict:
    visibility = normalize_visibility(getattr(record, "_api_visibility", "private"))
    return {
        "id": record.id,
        "visibility": visibility,
        "tags": extract_tags_from_message(record),
        "preview": preview_text(record.content or ""),
        "created_at": record.timestamp.isoformat() + "Z" if record.timestamp else None,
        "user": {
            "id": record.sender.id if record.sender else record.sender_id,
            "username": record.sender.username if record.sender else "",
        },
        "content": content_payload(record, text_source=text_source),
    }


def records_response(rows: list[Message], *, limit: int, text_source: str) -> dict:
    has_more = len(rows) > limit
    return {
        "items": [record_payload(record, text_source=text_source) for record in rows[:limit]],
        "has_more": has_more,
    }


def render_content_html(record: Message) -> str:
    text_value = escape(str(record.content or ""))
    return f'<pre class="notice-text-content">{text_value}</pre>'


def render_notice_html(records: list[Message]) -> str:
    html_parts = ['<div class="notice-render-container">']
    for record in records:
        content_html = render_content_html(record)
        tags = extract_tags_from_message(record)
        tag_html = " ".join([f'<span class="tag-pill">#{escape(tag)}</span>' for tag in tags])
        username = escape(record.sender.username if record.sender else "用户")
        date_text = record.timestamp.strftime("%Y-%m-%d %H:%M") if record.timestamp else "未知时间"
        preview = escape(preview_text(record.content or "")) or "无预览内容"
        html_parts.append(
            f"""
            <article class="notice-item" id="notice-record-{record.id}">
                <div class="notice-head">
                    <strong>{username}</strong>
                    <span class="notice-date">{date_text}</span>
                </div>
                <div class="notice-preview">{preview}</div>
                <div class="notice-tags">
                    {tag_html}
                </div>
                <div class="notice-content">
                    {content_html}
                </div>
            </article>
            """
        )
    html_parts.append("</div>")
    return "".join(html_parts)
