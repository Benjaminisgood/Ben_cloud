from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from ..core.config import Settings, get_settings
from ..models import VinylRecord
from ..repositories.records_repo import list_records

logger = logging.getLogger(__name__)
_SYNC_ACTOR = "oss-sync"


def normalize_oss_path(settings: Settings, oss_path: str) -> str:
    normalized = oss_path.strip()
    if not normalized:
        return ""

    base = settings.OSS_PUBLIC_BASE_URL
    if base and normalized.startswith(("http://", "https://")):
        base_prefix = f"{base.rstrip('/')}/"
        if normalized.startswith(base_prefix):
            normalized = normalized[len(base_prefix) :]
        else:
            return normalized

    normalized = normalized.lstrip("/")
    prefix = settings.OSS_PREFIX
    if prefix and normalized.startswith(f"{prefix}/"):
        normalized = normalized[len(prefix) + 1 :]
    return normalized


def _derive_title(oss_path: str) -> str:
    filename = oss_path.rsplit("/", 1)[-1]
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]
    filename = filename.replace("-", " ").replace("_", " ").strip()
    return filename[:120] or "未命名唱片"


def _oss_endpoint(settings: Settings) -> str:
    endpoint = settings.ALIYUN_OSS_ENDPOINT.strip()
    if endpoint and not endpoint.startswith(("http://", "https://")):
        return f"https://{endpoint}"
    return endpoint


def _is_supported_media_file(settings: Settings, oss_path: str) -> bool:
    lowered = oss_path.lower()
    return any(lowered.endswith(ext) for ext in settings.OSS_ALLOWED_EXTENSIONS)


def _list_matching_object_keys(settings: Settings) -> list[str]:
    if not settings.OSS_SYNC_ENABLED:
        return []

    try:
        import oss2  # type: ignore
    except ImportError as exc:
        raise RuntimeError("oss2_not_installed") from exc

    auth = oss2.Auth(settings.ALIYUN_OSS_ACCESS_KEY_ID, settings.ALIYUN_OSS_ACCESS_KEY_SECRET)
    bucket = oss2.Bucket(auth, _oss_endpoint(settings), settings.ALIYUN_OSS_BUCKET)
    prefix = f"{settings.OSS_PREFIX}/" if settings.OSS_PREFIX else ""

    normalized_paths: list[str] = []
    for item in oss2.ObjectIteratorV2(bucket, prefix=prefix):
        key = str(getattr(item, "key", "")).strip()
        if not key or key.endswith("/"):
            continue
        normalized = normalize_oss_path(settings, key)
        if not normalized or not _is_supported_media_file(settings, normalized):
            continue
        normalized_paths.append(normalized)
    return normalized_paths


def sync_missing_records_from_oss(db: Session) -> int:
    settings = get_settings()
    if not settings.OSS_SYNC_ENABLED:
        return 0

    try:
        object_paths = _list_matching_object_keys(settings)
    except Exception:
        logger.exception("Failed to list OSS objects for Benvinyl auto-import.")
        return 0

    if not object_paths:
        return 0

    existing_paths = set()
    for record in list_records(db):
        existing_paths.add(record.oss_path)
        existing_paths.add(normalize_oss_path(settings, record.oss_path))

    pending_paths = sorted({path for path in object_paths if path not in existing_paths})
    if not pending_paths:
        return 0

    for oss_path in pending_paths:
        db.add(
            VinylRecord(
                title=_derive_title(oss_path),
                note="",
                oss_path=oss_path,
                added_by=_SYNC_ACTOR,
                is_trashed=False,
                selected_for_date=None,
            )
        )

    db.commit()
    return len(pending_paths)
