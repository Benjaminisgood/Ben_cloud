from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from benreel_api.core.config import Settings, get_settings
from benreel_api.models import VideoItem
from benreel_api.repositories.video_items_repo import (
    get_video_item,
    list_video_items,
    list_video_items_by_asset_urls,
    list_video_items_by_external_ids,
)
from benreel_api.schemas.dashboard import DashboardSnapshot, MetricCard, ProgramVideo, TrashVideo, ViewerState
from benreel_api.schemas.video_item import VideoItemStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ManifestVideo:
    external_id: str
    title: str
    asset_url: str
    poster_url: str | None
    summary: str | None
    duration_label: str | None
    library_order: int


def _stable_hex(seed: str) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _normalize_manifest_payload(payload: object) -> list[dict[str, object]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("videos"), list):
            return [item for item in payload["videos"] if isinstance(item, dict)]
        if isinstance(payload.get("items"), list):
            return [item for item in payload["items"] if isinstance(item, dict)]
        return []
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    return []


def load_manifest_videos(manifest_path: Path) -> list[ManifestVideo]:
    if not manifest_path.exists():
        return []

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    videos: list[ManifestVideo] = []
    for index, raw in enumerate(_normalize_manifest_payload(payload), start=1):
        asset_url = str(raw.get("url") or raw.get("asset_url") or "").strip()
        if not asset_url:
            continue
        external_id = str(raw.get("id") or raw.get("external_id") or _stable_hex(asset_url)[:16]).strip()
        title = str(raw.get("title") or external_id).strip()
        videos.append(
            ManifestVideo(
                external_id=external_id,
                title=title,
                asset_url=asset_url,
                poster_url=str(raw.get("poster_url") or raw.get("poster") or "").strip() or None,
                summary=str(raw.get("summary") or raw.get("description") or "").strip() or None,
                duration_label=str(raw.get("duration_label") or raw.get("duration") or "").strip() or None,
                library_order=index,
            )
        )
    return videos


def _derive_title(value: str) -> str:
    filename = value.rsplit("/", 1)[-1]
    if "." in filename:
        filename = filename.rsplit(".", 1)[0]
    filename = filename.replace("-", " ").replace("_", " ").strip()
    return filename[:200] or "未命名胶卷"


def _normalize_oss_path(settings: Settings, oss_path: str) -> str:
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


def _resolve_asset_url(settings: Settings, oss_path: str) -> str:
    if oss_path.startswith(("http://", "https://")):
        return oss_path
    base = settings.OSS_PUBLIC_BASE_URL
    if base:
        return f"{base}/{_normalize_oss_path(settings, oss_path).lstrip('/')}"
    return oss_path


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
        normalized = _normalize_oss_path(settings, key)
        if not normalized or not _is_supported_media_file(settings, normalized):
            continue
        normalized_paths.append(normalized)
    return normalized_paths


def sync_video_library(db: Session, manifest_path: Path) -> str:
    manifest_videos = load_manifest_videos(manifest_path)
    existing = {
        item.external_id: item
        for item in list_video_items_by_external_ids(db, [video.external_id for video in manifest_videos])
    }

    dirty = False
    for video in manifest_videos:
        current = existing.get(video.external_id)
        if current is None:
            db.add(
                VideoItem(
                    external_id=video.external_id,
                    title=video.title,
                    asset_url=video.asset_url,
                    poster_url=video.poster_url,
                    summary=video.summary,
                    duration_label=video.duration_label,
                    library_order=video.library_order,
                    status="active",
                )
            )
            dirty = True
            continue

        fields = {
            "title": video.title,
            "asset_url": video.asset_url,
            "poster_url": video.poster_url,
            "summary": video.summary,
            "duration_label": video.duration_label,
            "library_order": video.library_order,
        }
        for field_name, value in fields.items():
            if getattr(current, field_name) != value:
                setattr(current, field_name, value)
                dirty = True

    if dirty:
        db.commit()

    return manifest_path.name


def sync_missing_videos_from_oss(db: Session) -> int:
    settings = get_settings()
    if not settings.OSS_SYNC_ENABLED:
        return 0

    try:
        object_paths = _list_matching_object_keys(settings)
    except Exception:
        logger.exception("Failed to list OSS objects for Benreel auto-import.")
        return 0

    if not object_paths:
        return 0

    asset_urls = [_resolve_asset_url(settings, oss_path) for oss_path in object_paths]
    existing_urls = {item.asset_url for item in list_video_items_by_asset_urls(db, asset_urls)}
    if len(existing_urls) == len(asset_urls):
        return 0

    next_library_order = max((item.library_order for item in list_video_items(db)), default=0) + 1
    inserted_count = 0
    for oss_path, asset_url in sorted(zip(object_paths, asset_urls), key=lambda item: item[0]):
        if asset_url in existing_urls:
            continue
        db.add(
            VideoItem(
                external_id=_stable_hex(f"oss::{asset_url}")[:16],
                title=_derive_title(oss_path),
                asset_url=asset_url,
                poster_url=None,
                summary=None,
                duration_label=None,
                library_order=next_library_order,
                status="active",
            )
        )
        next_library_order += 1
        inserted_count += 1

    if inserted_count:
        db.commit()
    return inserted_count


def sync_video_sources(db: Session, manifest_path: Path) -> str:
    source_label = sync_video_library(db, manifest_path) if manifest_path.exists() else ""
    imported_count = sync_missing_videos_from_oss(db)
    if imported_count and source_label:
        return f"{source_label} + OSS"
    if imported_count:
        return "Aliyun OSS"
    return source_label or manifest_path.name


def _restored_today(item: VideoItem, today: date) -> bool:
    return bool(item.restored_at and item.restored_at.date() == today)


def _rank_for_day(item: VideoItem, today: date) -> tuple[int, str, int]:
    restored_rank = 0 if _restored_today(item, today) else 1
    return (restored_rank, _stable_hex(f"{today.isoformat()}::{item.external_id}"), item.library_order)


def _viewer_state(viewer: dict[str, str] | None) -> ViewerState:
    username = viewer["username"] if viewer and viewer.get("username") else None
    role = viewer["role"] if viewer and viewer.get("role") else "guest"
    return ViewerState(username=username, role=role, is_admin=role == "admin")


def build_dashboard_snapshot(
    db: Session,
    *,
    manifest_path: Path,
    daily_video_count: int,
    viewer: dict[str, str] | None,
    today: date | None = None,
) -> DashboardSnapshot:
    target_day = today or datetime.now(UTC).date()
    source_label = sync_video_sources(db, manifest_path)

    active_videos = list_video_items(db, status="active")
    program_items = sorted(active_videos, key=lambda item: _rank_for_day(item, target_day))[: max(1, daily_video_count)]
    viewer_state = _viewer_state(viewer)

    summary = [
        MetricCard(label="片库总数", value=str(len(active_videos)), hint="当前仍对外可见的视频卷数"),
        MetricCard(label="今日节目", value=str(len(program_items)), hint="今天固定上线的胶卷数量"),
        MetricCard(
            label="垃圾桶",
            value=str(len(list_video_items(db, status="trashed"))) if viewer_state.is_admin else "隐藏",
            hint="管理员可随时捡回下线的胶卷",
        ),
    ]

    trash_items = list_video_items(db, status="trashed") if viewer_state.is_admin else []
    trash = [
        TrashVideo(
            id=item.id,
            title=item.title,
            summary=item.summary,
            poster_url=item.poster_url,
            trashed_at=item.trashed_at,
        )
        for item in sorted(trash_items, key=lambda item: item.trashed_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    ]

    program = [
        ProgramVideo(
            id=item.id,
            title=item.title,
            summary=item.summary,
            asset_url=item.asset_url,
            poster_url=item.poster_url,
            duration_label=item.duration_label,
            reel_label=f"第 {index} 卷",
            restored_today=_restored_today(item, target_day),
        )
        for index, item in enumerate(program_items, start=1)
    ]

    return DashboardSnapshot(
        source=source_label,
        day_label=target_day.strftime("%Y-%m-%d"),
        summary=summary,
        program=program,
        trash=trash,
        viewer=viewer_state,
    )


def update_video_status(
    db: Session,
    *,
    video_id: int,
    status: VideoItemStatus,
    actor: str,
) -> VideoItem:
    item = get_video_item(db, video_id)
    if item is None:
        raise ValueError(f"Video {video_id} not found")

    now = datetime.now(UTC)
    if status == item.status:
        return item

    if status == "trashed":
        item.status = "trashed"
        item.trashed_at = now
        item.trashed_by = actor
    else:
        item.status = "active"
        item.restored_at = now
        item.restored_by = actor

    db.commit()
    db.refresh(item)
    return item
