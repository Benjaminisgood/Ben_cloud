from __future__ import annotations

from ..models import GeneratedAsset, Record, User
from ..utils.file_types import detect_file_type

VALID_FILE_TYPES = {"text", "web", "image", "video", "audio", "log", "database", "archive", "document", "file"}


def content_file_type(record: Record) -> str:
    if record.content:
        if record.content.kind == "text":
            return "text"
        return detect_file_type(record.content.content_type, record.content.filename)
    return "file"


def asset_file_type(asset: GeneratedAsset) -> str:
    if asset.kind == "blog_html":
        return "web"
    return detect_file_type(asset.content_type, asset.ext)


def _media_type_from_file_type(file_type: str) -> str:
    if file_type in {"image", "video", "audio"}:
        return file_type
    return "file"


def record_echo_item(record: Record, viewer: User) -> dict:
    record_file_type = content_file_type(record)
    content = record.content
    content_out = None
    if content:
        content_out = {
            "id": content.id,
            "kind": content.kind,
            "file_type": record_file_type,
            "media_type": _media_type_from_file_type(record_file_type),
            "filename": content.filename or "",
            "content_type": content.content_type or "",
            "size_bytes": int(content.size_bytes or 0),
            "blob_url": f"/api/contents/{content.id}/blob",
            "text": str(content.text_content or "")[:500] if content.kind == "text" else None,
        }
    return {
        "id": int(record.id or 0),
        "entry_type": "record",
        "file_type": record_file_type,
        "created_at": record.created_at.isoformat() + "Z" if record.created_at else None,
        "record": {
            "id": record.id,
            "visibility": record.visibility,
            "tags": record.get_tags(),
            "preview": record.preview or "",
            "created_at": record.created_at.isoformat() + "Z" if record.created_at else None,
            "user": {
                "id": record.user.id if record.user else record.user_id,
                "username": record.user.username if record.user else "",
            },
            "can_edit": viewer.id == record.user_id,
            "can_clone": viewer.id == record.user_id,
            "content": content_out,
        },
    }


def asset_echo_item(asset: GeneratedAsset) -> dict:
    file_type = asset_file_type(asset)
    return {
        "id": int(asset.id or 0),
        "entry_type": "asset",
        "file_type": file_type,
        "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
        "asset": {
            "id": asset.id,
            "kind": asset.kind,
            "title": asset.title or "",
            "file_type": file_type,
            "visibility": asset.visibility,
            "source_day": str(asset.source_day) if asset.source_day else None,
            "blob_url": f"/api/generated-assets/{asset.id}/blob",
            "content_type": asset.content_type or "",
            "ext": asset.ext or "",
            "size_bytes": int(asset.size_bytes or 0),
            "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
            "user": {
                "id": asset.user.id if asset.user else asset.user_id,
                "username": asset.user.username if asset.user else "",
            },
            "can_edit": False,
            "can_delete": False,
        },
    }


def _entry_sort_key(entry: dict) -> tuple:
    created_at = str(entry.get("created_at") or "")
    kind_rank = 1 if entry.get("entry_type") == "record" else 0
    entry_id = int(entry.get("id") or 0)
    return (created_at, kind_rank, entry_id)


def build_echoes_response(
    *,
    records: list[Record],
    assets: list[GeneratedAsset],
    viewer: User,
    file_type: str,
    scope: str,
    limit: int,
) -> dict:
    entries = [record_echo_item(record, viewer) for record in records] + [asset_echo_item(asset) for asset in assets]
    if file_type:
        entries = [entry for entry in entries if entry.get("file_type") == file_type]
    entries.sort(key=_entry_sort_key, reverse=True)

    has_more = len(entries) > limit
    page_entries = entries[:limit]
    next_cursor = None
    if has_more and page_entries:
        last = page_entries[-1]
        next_cursor = {
            "created_at": last.get("created_at"),
            "entry_type": last.get("entry_type"),
            "id": int(last.get("id") or 0),
        }

    page_records = [entry for entry in page_entries if entry.get("entry_type") == "record"]
    page_assets = [entry for entry in page_entries if entry.get("entry_type") == "asset"]
    return {
        "scope": scope,
        "entries": page_entries,
        "next_cursor": next_cursor,
        "has_more": has_more,
        # Keep compatibility for older clients that read split lists.
        "records": page_records,
        "assets": page_assets,
    }
