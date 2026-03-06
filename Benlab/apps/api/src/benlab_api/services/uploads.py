from __future__ import annotations

import os
import uuid
from pathlib import Path

from fastapi import UploadFile

from benlab_api.core.config import get_settings


ALLOWED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"}


def ensure_dirs() -> None:
    get_settings().ensure_data_dirs()


def _safe_name(original_name: str) -> str:
    base = os.path.basename(original_name or "upload.bin")
    stem, ext = os.path.splitext(base)
    ext = ext.lower()[:10]
    stem = "".join(ch for ch in stem if ch.isalnum() or ch in {"-", "_"})
    stem = stem[:40] or "file"
    return f"{stem}-{uuid.uuid4().hex[:12]}{ext}"


def save_upload(upload: UploadFile) -> str:
    settings = get_settings()
    ensure_dirs()
    filename = _safe_name(upload.filename or "upload.bin")
    path = settings.ATTACHMENTS_DIR / filename
    with path.open("wb") as f:
        while True:
            chunk = upload.file.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
    return filename


def remove_upload(filename: str) -> None:
    settings = get_settings()
    if not filename:
        return
    if not settings.ATTACHMENTS_DIR.exists():
        return
    path = settings.ATTACHMENTS_DIR / os.path.basename(filename)
    if path.exists() and path.is_file():
        path.unlink(missing_ok=True)


def abs_attachment_path(filename: str) -> Path:
    settings = get_settings()
    return settings.ATTACHMENTS_DIR / os.path.basename(filename)
