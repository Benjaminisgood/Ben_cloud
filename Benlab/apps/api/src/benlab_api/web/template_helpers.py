from __future__ import annotations

import json
from collections.abc import Iterable
from html import escape

from markupsafe import Markup

from benlab_api.core.constants import ITEM_STATUS_CHOICES, LOCATION_STATUS_CHOICES, LOCATION_USAGE_TAG_CHOICES


MEDIA_KIND_LABELS = {
    "image": "图片",
    "video": "视频",
    "audio": "音频",
    "file": "文件",
    "external": "外链",
}

LOCATION_USAGE_LABELS = {
    "study": "学习",
    "leisure": "休闲",
    "event": "活动",
    "public": "公共",
    "rental": "出租",
    "storage": "储物",
    "travel": "旅行",
    "residence": "居住",
    "other": "其他",
}


def normalize_item_stock_status(value: str | None) -> str:
    token = (value or "").strip()
    return token if token in ITEM_STATUS_CHOICES else ITEM_STATUS_CHOICES[0]


def normalize_location_status(value: str | None) -> str:
    token = (value or "").strip()
    return token if token in LOCATION_STATUS_CHOICES else LOCATION_STATUS_CHOICES[0]


def stock_status_intent(status: str | None) -> str:
    status = normalize_item_stock_status(status)
    if status in {"少量", "借出"}:
        return "warning"
    if status in {"用完", "舍弃"}:
        return "critical"
    return "neutral"


def location_status_intent(status: str | None) -> str:
    status = normalize_location_status(status)
    if status in {"脏", "报修"}:
        return "warning"
    if status in {"危险", "禁止"}:
        return "critical"
    return "positive" if status == "正常" else "neutral"


def status_intent(status: str | None) -> str:
    return location_status_intent(status)


def is_location_dirty(status: str | None) -> bool:
    return normalize_location_status(status) in {"脏", "报修", "危险", "禁止"}


def is_item_alert_status(status: str | None) -> bool:
    return normalize_item_stock_status(status) in {"少量", "用完", "借出", "舍弃"}


def item_alert_level(status: str | None) -> str:
    normalized = normalize_item_stock_status(status)
    if normalized in {"用完", "舍弃"}:
        return "danger"
    if normalized in {"少量", "借出"}:
        return "warning"
    return "secondary"


def item_alert_action_label(status: str | None) -> str:
    normalized = normalize_item_stock_status(status)
    if normalized == "用完":
        return "去补货"
    if normalized == "少量":
        return "快补货"
    if normalized == "借出":
        return "跟进归还"
    if normalized == "舍弃":
        return "检查替代品"
    return "查看"


def feature_intent(feature: str | None) -> str:
    token = (feature or "").strip()
    if "公共" in token:
        return "public"
    if "私人" in token:
        return "private"
    return "neutral"


def feature_tone(feature: str | None) -> str:
    return feature_intent(feature)


def media_kind(ref: str | None) -> str:
    token = (ref or "").lower()
    if any(token.endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"]):
        return "image"
    if any(token.endswith(ext) for ext in [".mp4", ".mov", ".m4v", ".webm", ".avi", ".mkv"]):
        return "video"
    if any(token.endswith(ext) for ext in [".mp3", ".wav", ".m4a", ".ogg", ".aac", ".flac"]):
        return "audio"
    if token.startswith("http://") or token.startswith("https://"):
        return "external"
    return "file"


def media_display_name(ref: str | None) -> str:
    token = (ref or "").strip()
    if not token:
        return ""
    return token.split("/")[-1]


def uploaded_attachment_url(ref: str | None) -> str:
    token = (ref or "").strip()
    if not token:
        return ""
    if token.startswith("http://") or token.startswith("https://"):
        return token
    return f"/attachments/{token}"


def uploaded_media_url(ref: str | None) -> str:
    return uploaded_attachment_url(ref)


def _normalize_gallery_entries(entries) -> list[dict]:
    normalized: list[dict] = []
    for entry in entries or []:
        if isinstance(entry, dict):
            url = entry.get("url") or entry.get("filename") or ""
            if not url:
                continue
            kind = entry.get("kind") or media_kind(url)
            normalized.append(
                {
                    "url": uploaded_media_url(url),
                    "kind": kind,
                    "display_name": entry.get("display_name") or media_display_name(url),
                }
            )
        elif hasattr(entry, "filename"):
            ref = getattr(entry, "filename", "")
            if ref:
                normalized.append(
                    {
                        "url": uploaded_media_url(ref),
                        "kind": media_kind(ref),
                        "display_name": media_display_name(ref),
                    }
                )
        elif isinstance(entry, str):
            normalized.append(
                {
                    "url": uploaded_media_url(entry),
                    "kind": media_kind(entry),
                    "display_name": media_display_name(entry),
                }
            )
    return normalized


def render_media_gallery(entries, gallery_id="gallery", media_kind_labels=None, empty_text="暂无媒体文件", options=None):
    rows = _normalize_gallery_entries(entries)
    if not rows:
        return Markup(f'<p class="text-muted mb-0">{escape(empty_text)}</p>')
    html_parts = [f'<div class="media-gallery" id="{escape(str(gallery_id))}"><ul class="list-unstyled mb-0">']
    for row in rows:
        url = escape(row["url"])
        name = escape(row.get("display_name") or row["url"])
        html_parts.append(f'<li><a href="{url}" target="_blank" rel="noopener">{name}</a></li>')
    html_parts.append("</ul></div>")
    return Markup("".join(html_parts))


def render_notification_entry(log):
    action = escape(getattr(log, "action_type", "操作") or "操作")
    details = escape(getattr(log, "details", "") or "")
    return Markup(f"<span>{action} {details}</span>")


def render_resource_entry(entry, kind="item"):
    name = escape(getattr(entry, "name", "") or getattr(entry, "title", "") or "记录")
    return Markup(f"<span>{name}</span>")


def render_user_log_entry(log):
    return render_notification_entry(log)


def is_http(value: str | None) -> bool:
    token = (value or "").strip().lower()
    return token.startswith("http://") or token.startswith("https://")


def event_relation_lookup(_events=None):
    return {}


def item_relation_lookup(_items=None):
    return {}


def relation_lookup(_entries=None):
    return {}


def _attachment_entries(owner) -> list[dict]:
    entries: list[dict] = []
    for att in getattr(owner, "attachments", []) or []:
        filename = getattr(att, "filename", "")
        if not filename:
            continue
        entries.append(
            {
                "url": uploaded_media_url(filename),
                "filename": filename,
                "kind": media_kind(filename),
                "display_name": media_display_name(filename),
            }
        )
    return entries


def item_media_entries(item):
    return _attachment_entries(item)


def location_media_entries(location):
    return _attachment_entries(location)


def event_media_entries(event):
    return _attachment_entries(event)


def default_form_state(event=None, *, location_ids=None, item_ids=None, participant_ids=None):
    location_ids = location_ids or []
    item_ids = item_ids or []
    participant_ids = participant_ids or []
    return {
        "title": getattr(event, "title", "") or "",
        "description": getattr(event, "description", "") or "",
        "visibility": getattr(event, "visibility", "personal") or "personal",
        "start_time": getattr(event, "start_time", None).strftime("%Y-%m-%dT%H:%M") if getattr(event, "start_time", None) else "",
        "end_time": getattr(event, "end_time", None).strftime("%Y-%m-%dT%H:%M") if getattr(event, "end_time", None) else "",
        "detail_link": getattr(event, "detail_link", "") or "",
        "allow_participant_edit": bool(getattr(event, "allow_participant_edit", False)),
        "location_ids": location_ids,
        "item_ids": item_ids,
        "participant_ids": participant_ids,
        "location_selection_touched": "0",
        "item_selection_touched": "0",
        "participant_selection_touched": "0",
        "start_time_touched": "0",
        "end_time_touched": "0",
        "external_attachment_urls": "",
    }


def default_graph_json() -> str:
    payload = {
        "nodes": [],
        "links": [],
    }
    return json.dumps(payload, ensure_ascii=False)

