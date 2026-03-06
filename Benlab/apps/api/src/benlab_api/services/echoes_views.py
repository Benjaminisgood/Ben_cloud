from __future__ import annotations

import mimetypes
from pathlib import Path

from benlab_api.models import Attachment, Member, Message
from benlab_api.services.records_service import extract_tags_from_message, preview_text
from benlab_api.services.uploads import abs_attachment_path

VALID_FILE_TYPES = {"text", "web", "image", "video", "audio", "log", "database", "archive", "document", "file"}


def _detect_attachment_file_type(filename: str) -> str:
    ext = Path(filename or "").suffix.lower()
    guessed = mimetypes.guess_type(filename or "")[0] or ""

    if guessed.startswith("image/"):
        return "image"
    if guessed.startswith("video/"):
        return "video"
    if guessed.startswith("audio/"):
        return "audio"
    if guessed.startswith("text/"):
        return "text"

    if ext in {".html", ".htm"}:
        return "web"
    if ext in {".log"}:
        return "log"
    if ext in {".db", ".sqlite", ".sqlite3"}:
        return "database"
    if ext in {".zip", ".tar", ".gz", ".bz2", ".xz", ".rar", ".7z"}:
        return "archive"
    if ext in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".md"}:
        return "document"
    return "file"


def _attachment_size_bytes(asset: Attachment) -> int:
    path = abs_attachment_path(asset.filename)
    if not path.exists() or not path.is_file():
        return 0
    return int(path.stat().st_size)


def record_echo_item(record: Message, viewer: Member) -> dict:
    text = str(record.content or "")
    content_out = {
        "id": record.id,
        "kind": "text",
        "file_type": "text",
        "filename": "",
        "content_type": "text/plain; charset=utf-8",
        "size_bytes": len(text.encode("utf-8")),
        "blob_url": f"/api/contents/{record.id}/blob",
        "text": text[:500],
    }
    return {
        "entry_type": "record",
        "file_type": "text",
        "record": {
            "id": record.id,
            "visibility": "private",
            "tags": extract_tags_from_message(record),
            "preview": preview_text(record.content or ""),
            "created_at": record.timestamp.isoformat() + "Z" if record.timestamp else None,
            "user": {
                "id": record.sender.id if record.sender else record.sender_id,
                "username": record.sender.username if record.sender else "",
            },
            "can_edit": viewer.id == record.sender_id,
            "content": content_out,
        },
    }


def asset_echo_item(asset: Attachment) -> dict:
    file_type = _detect_attachment_file_type(asset.filename)
    return {
        "entry_type": "asset",
        "file_type": file_type,
        "asset": {
            "id": asset.id,
            "kind": "attachment",
            "title": asset.filename or "",
            "file_type": file_type,
            "visibility": "private",
            "source_day": str(asset.created_at.date()) if asset.created_at else None,
            "blob_url": f"/api/generated-assets/{asset.id}/blob",
            "size_bytes": _attachment_size_bytes(asset),
            "created_at": asset.created_at.isoformat() + "Z" if asset.created_at else None,
        },
    }


def build_echoes_response(
    *,
    records: list[Message],
    assets: list[Attachment],
    viewer: Member,
    file_type: str,
    limit: int,
) -> dict:
    if file_type:
        records = [record for record in records if "text" == file_type]
        assets = [asset for asset in assets if _detect_attachment_file_type(asset.filename) == file_type]

    has_more_records = len(records) > limit
    has_more_assets = len(assets) > limit

    return {
        "records": [record_echo_item(record, viewer) for record in records[:limit]],
        "assets": [asset_echo_item(asset) for asset in assets[:limit]],
        "has_more": has_more_records or has_more_assets,
    }
