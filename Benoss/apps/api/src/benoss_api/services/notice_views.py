from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from html import escape
from urllib.parse import quote_plus
from zoneinfo import ZoneInfo

from ..models import Content, Record
from ..utils.runtime_settings import get_setting_str

_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")
_VIDEO_EXTENSIONS = (".mp4", ".mov", ".m4v", ".webm", ".ogg")
_AUDIO_EXTENSIONS = (".mp3", ".m4a", ".wav", ".flac", ".ogg", ".aac")


def parse_user_id_filter(user_id: str) -> int | None:
    return int(user_id) if user_id and user_id.isdigit() else None


def parse_day_filter(day: str) -> tuple[datetime | None, datetime | None]:
    if not day:
        return None, None
    start = datetime.strptime(day, "%Y-%m-%d")
    return start, start + timedelta(days=1)


@lru_cache(maxsize=1)
def _notice_timezone():
    tz_name = str(get_setting_str("DIGEST_TIMEZONE", default="Asia/Shanghai") or "Asia/Shanghai").strip() or "Asia/Shanghai"
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return UTC


def _notice_local_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        source = value.replace(tzinfo=UTC)
    else:
        source = value.astimezone(UTC)
    return source.astimezone(_notice_timezone())


def _get_oss_text(oss_key: str) -> str:
    from ..utils.oss import get_object_bytes

    raw = get_object_bytes(oss_key)
    return raw.decode("utf-8", errors="replace")


def _load_text_content(content: Content, *, text_source: str) -> str:
    if text_source != "oss":
        return str(content.text_content or "")
    try:
        return _get_oss_text(content.oss_key)
    except Exception:
        return str(content.text_content or "")


def content_payload(content: Content | None, *, text_source: str) -> dict | None:
    if content is None:
        return None
    if content.kind == "text":
        return {
            "kind": "text",
            "text": _load_text_content(content, text_source=text_source),
            "size_bytes": int(content.size_bytes or 0),
        }
    return {
        "kind": "file",
        "file_type": content.file_type or "file",
        "filename": content.filename or "",
        "content_type": content.content_type or "",
        "size_bytes": int(content.size_bytes or 0),
        "blob_url": f"/api/contents/{content.id}/blob",
    }


def record_payload(record: Record, *, text_source: str) -> dict:
    return {
        "id": record.id,
        "visibility": record.visibility,
        "tags": record.get_tags(),
        "preview": record.preview or "",
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else None,
        "user": {
            "id": record.user.id if record.user else record.user_id,
            "username": record.user.username if record.user else "",
        },
        "content": content_payload(record.content, text_source=text_source),
    }


def records_response(rows: list[Record], *, limit: int, text_source: str) -> dict:
    has_more = len(rows) > limit
    return {
        "items": [record_payload(record, text_source=text_source) for record in rows[:limit]],
        "has_more": has_more,
    }


def _build_tag_link(tag: str, *, class_name: str = "tag-pill tag-pill-inline") -> str:
    safe_tag = str(tag or "").strip()
    if not safe_tag:
        return ""
    tag_html = escape(safe_tag)
    href = f"/notice?tag={quote_plus(safe_tag)}"
    return f'<a class="{escape(class_name)}" href="{href}" data-notice-tag="{tag_html}">#{tag_html}</a>'


def _format_size(size_bytes: int) -> str:
    value = max(0, int(size_bytes or 0))
    if value < 1024:
        return f"{value} B"
    if value < 1024 * 1024:
        return f"{value / 1024:.1f} KB"
    if value < 1024 * 1024 * 1024:
        return f"{value / (1024 * 1024):.1f} MB"
    return f"{value / (1024 * 1024 * 1024):.2f} GB"


def _display_kind(content: Content) -> str:
    file_type = str(content.file_type or "").strip().lower()
    content_type = str(content.content_type or "").split(";", 1)[0].strip().lower()
    filename = str(content.filename or "").strip().lower()
    if file_type == "image" or content_type.startswith("image/") or filename.endswith(_IMAGE_EXTENSIONS):
        return "image"
    if file_type == "video" or content_type.startswith("video/") or filename.endswith(_VIDEO_EXTENSIONS):
        return "video"
    if file_type == "audio" or content_type.startswith("audio/") or filename.endswith(_AUDIO_EXTENSIONS):
        return "audio"
    return "file"


def _context_user_name(record: Record) -> str:
    if record.user and record.user.username:
        return str(record.user.username)
    if record.user_id:
        return f"用户#{record.user_id}"
    return "用户"


def _clip_text(value: str, *, max_len: int = 44) -> str:
    text = str(value or "").strip()
    if len(text) <= max_len:
        return text
    return f"{text[:max_len - 3]}..."


def render_content_html(content: Content | None) -> str:
    if content is None:
        return '<p class="muted">无内容</p>'
    if content.kind == "text":
        text_value = _load_text_content(content, text_source="oss")
        return f'<pre class="notice-text-content">{escape(text_value)}</pre>'

    filename = escape(content.filename or "文件")
    blob_url = f"/api/contents/{content.id}/blob"
    file_meta = escape(f"{content.file_type or 'file'} · {_format_size(int(content.size_bytes or 0))}")
    display_kind = _display_kind(content)

    if display_kind == "image":
        return (
            f'<figure class="notice-media notice-media-image">'
            f'<div class="notice-media-stage">'
            f'<a class="notice-media-link" href="{blob_url}" target="_blank" rel="noreferrer noopener">'
            f'<img src="{blob_url}" alt="{filename}">'
            f"</a>"
            f"</div>"
            f'<figcaption class="notice-media-caption">'
            f'<span class="notice-media-caption-main">'
            f'<span class="notice-media-name">{filename}</span>'
            f'<span class="notice-file-meta">{file_meta}</span>'
            f"</span>"
            f'<a class="notice-media-action" href="{blob_url}" target="_blank" rel="noreferrer noopener">打开原图</a>'
            f"</figcaption>"
            f"</figure>"
        )

    if display_kind == "video":
        return (
            f'<figure class="notice-media notice-media-video">'
            f'<div class="notice-media-stage">'
            f'<video controls preload="metadata" src="{blob_url}"></video>'
            f"</div>"
            f'<figcaption class="notice-media-caption">'
            f'<span class="notice-media-caption-main">'
            f'<span class="notice-media-name">{filename}</span>'
            f'<span class="notice-file-meta">{file_meta}</span>'
            f"</span>"
            f'<a class="notice-media-action" href="{blob_url}" target="_blank" rel="noreferrer noopener">新窗口播放</a>'
            f"</figcaption>"
            f"</figure>"
        )

    if display_kind == "audio":
        return (
            f'<section class="notice-media notice-media-audio">'
            f'<div class="notice-audio-head">'
            f'<p class="notice-audio-label">AUDIO</p>'
            f'<div class="notice-audio-main">'
            f'<p class="notice-media-name">{filename}</p>'
            f'<p class="notice-file-meta">{file_meta}</p>'
            f"</div>"
            f'<a class="notice-media-action" href="{blob_url}" target="_blank" rel="noreferrer noopener">新窗口打开</a>'
            f"</div>"
            f'<audio class="notice-audio-control" controls preload="none" src="{blob_url}"></audio>'
            f"</section>"
        )

    return (
        f'<section class="notice-file-card">'
        f'<p class="notice-file-name">{filename}</p>'
        f'<p class="notice-file-meta">{file_meta}</p>'
        f'<p class="notice-file-actions">'
        f'<a class="notice-media-action" href="{blob_url}" target="_blank" rel="noreferrer noopener">下载文件</a>'
        f"</p>"
        f"</section>"
    )


def render_notice_html(records: list[Record], *, viewer_user_id: int | None = None) -> str:
    if not records:
        return (
            '<div class="notice-render">'
            '<div class="notice-reader-layout">'
            '<section class="notice-main-flow">'
            '<section class="notice-render-summary">'
            "<h2>暂无匹配记录</h2>"
            '<p class="notice-summary-line">请调整筛选条件后重试。</p>'
            "</section>"
            "</section>"
            '<aside class="notice-context-rail">'
            '<div class="notice-context-head">'
            '<p class="notice-context-title">阅读导航</p>'
            '<div class="notice-context-badges"><span class="notice-context-badge">0 条记录</span></div>'
            "</div>"
            "</aside>"
            "</div>"
            "</div>"
        )

    grouped_by_day: dict[str, list[Record]] = {}
    unique_users: set[int] = set()
    tag_counter: Counter[str] = Counter()

    for record in records:
        local_created_at = _notice_local_datetime(record.created_at)
        day_key = local_created_at.strftime("%Y-%m-%d") if local_created_at else "未知日期"
        grouped_by_day.setdefault(day_key, []).append(record)
        if record.user_id:
            unique_users.add(int(record.user_id))
        for tag in record.get_tags():
            cleaned = str(tag or "").strip()
            if cleaned:
                tag_counter[cleaned] += 1

    total_count = len(records)
    day_count = len(grouped_by_day)
    top_tags = tag_counter.most_common(8)
    summary_line = f"{day_count} 天 · {len(unique_users)} 位成员 · {total_count} 条记录"

    main_parts: list[str] = [
        '<section class="notice-main-flow">',
        '<section class="notice-render-summary">',
        "<h2>阅读结果</h2>",
        f'<p class="notice-summary-line">{escape(summary_line)}</p>',
        "</section>",
    ]
    side_parts: list[str] = [
        '<aside class="notice-context-rail">',
        '<div class="notice-context-head">',
        '<p class="notice-context-title">阅读导航</p>',
        '<div class="notice-context-badges">',
        f'<span class="notice-context-badge">{total_count} 条记录</span>',
        f'<span class="notice-context-badge">{day_count} 天</span>',
        "</div>",
    ]

    if top_tags:
        side_parts.append('<div class="notice-context-hot-tags">')
        for tag_name, _count in top_tags:
            side_parts.append(_build_tag_link(tag_name, class_name="tag-pill tag-pill-inline notice-side-tag"))
        side_parts.append("</div>")

    side_parts.extend(["</div>", '<div class="notice-context-list">'])

    for day_key, day_records in grouped_by_day.items():
        escaped_day = escape(day_key)
        main_parts.extend(
            [
                f'<section class="notice-day" data-day="{escaped_day}">',
                f'<h3 class="notice-day-label">{escaped_day}</h3>',
            ]
        )
        side_parts.append(f'<h4 class="notice-context-day">{escaped_day}</h4>')

        for record in day_records:
            record_id = int(record.id or 0)
            record_anchor = f"#notice-record-{record_id}"
            user_name = escape(_context_user_name(record))
            local_created_at = _notice_local_datetime(record.created_at)
            time_text = local_created_at.strftime("%H:%M") if local_created_at else "--:--"
            preview_text = str(record.preview or "").strip() or "无预览内容"
            tags = record.get_tags()
            content_html = render_content_html(record.content)
            can_edit = viewer_user_id is not None and int(record.user_id or 0) == int(viewer_user_id)

            main_parts.append(
                f'<article class="notice-block" id="notice-record-{record_id}">'
                f'<div class="notice-block-body">{content_html}</div>'
                f"</article>"
            )

            side_actions_items: list[str] = []
            if can_edit:
                side_actions_items.append(
                    f'<button type="button" class="bubble" data-action="edit-record" data-record-id="{record_id}">编辑记录</button>'
                )
            side_actions_items.extend(filter(None, (_build_tag_link(tag, class_name="bubble") for tag in tags[:3])))
            side_actions = " ".join(side_actions_items)
            side_actions_html = f'<p class="notice-context-actions">{side_actions}</p>' if side_actions else ""
            side_parts.append(
                f'<article class="notice-context-item">'
                f'<a class="notice-context-link" href="{record_anchor}" data-notice-anchor="{record_anchor}">'
                f'<span class="notice-context-time">{escape(time_text)}</span>'
                f'<span class="notice-context-user">{user_name}</span>'
                f'<span class="notice-context-record">{escape(_clip_text(preview_text))}</span>'
                f"</a>"
                f"{side_actions_html}"
                f"</article>"
            )

        main_parts.append("</section>")

    main_parts.append("</section>")
    side_parts.extend(["</div>", "</aside>"])

    return (
        '<div class="notice-render">'
        '<div class="notice-reader-layout">'
        f'{"".join(main_parts)}'
        f'{"".join(side_parts)}'
        "</div>"
        "</div>"
    )
