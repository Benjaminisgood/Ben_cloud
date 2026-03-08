
from __future__ import annotations

import random
from datetime import date, datetime
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..repositories.photos_repo import (
    count_photos,
    count_trashed_photos,
    list_candidate_photos,
    list_selected_photos,
    list_trashed_photos,
)
from ..schemas.dashboard import DashboardSnapshot, DeskPhotoCard, SummaryMetric, TrashPhotoCard
from .oss_sync import sync_missing_photos_from_oss
from .photos import resolve_image_url

_DESK_SLOTS: list[tuple[int, int, int]] = [
    (6, 78, -15),
    (21, 42, 9),
    (39, 86, -6),
    (56, 34, 13),
    (72, 82, -11),
    (18, 148, 7),
    (47, 158, -10),
    (68, 142, 5),
    (31, 228, 12),
    (58, 248, -8),
]
_ACCENTS = ["#f8d16a", "#ef8c6c", "#79c7b6", "#7e8ef1", "#f4a1c1", "#89b96d"]


def _daily_limit() -> int:
    return max(get_settings().DAILY_PHOTO_COUNT, 1)


def _short_source_label(oss_path: str) -> str:
    parsed = urlparse(oss_path)
    if parsed.netloc:
        return parsed.netloc
    parts = [part for part in oss_path.split("/") if part]
    if not parts:
        return "OSS"
    return "/".join(parts[-2:])


def ensure_daily_selection(db: Session, *, display_date: date | None = None) -> None:
    target_date = display_date or date.today()
    daily_limit = _daily_limit()
    current_selection = list_selected_photos(db, display_date=target_date, include_trashed=True)
    if len(current_selection) >= daily_limit:
        return

    candidates = list_candidate_photos(db, exclude_ids={photo.id for photo in current_selection})
    if not candidates:
        return

    rng = random.Random(f"benphoto:{target_date.isoformat()}")
    candidates = sorted(candidates, key=lambda photo: (photo.created_at, photo.id))
    rng.shuffle(candidates)
    remaining = daily_limit - len(current_selection)
    for photo in candidates[:remaining]:
        photo.selected_for_date = target_date
    db.commit()


def _build_desk_cards(db: Session, *, display_date: date) -> list[DeskPhotoCard]:
    settings = get_settings()
    photos = list_selected_photos(db, display_date=display_date, include_trashed=False)
    ordered = sorted(photos, key=lambda photo: photo.id)
    random.Random(f"desk-order:{display_date.isoformat()}").shuffle(ordered)

    cards: list[DeskPhotoCard] = []
    for index, photo in enumerate(ordered):
        slot_x, slot_y, slot_rotation = _DESK_SLOTS[index % len(_DESK_SLOTS)]
        jitter = random.Random(f"desk-card:{display_date.isoformat()}:{photo.id}")
        cards.append(
            DeskPhotoCard(
                id=photo.id,
                title=photo.title,
                caption=photo.caption,
                image_url=resolve_image_url(settings, photo.oss_path),
                source_label=_short_source_label(photo.oss_path),
                added_by=photo.added_by,
                x_pct=max(4, min(78, slot_x + jitter.randint(-4, 4))),
                y_px=max(24, slot_y + jitter.randint(-18, 18)),
                rotation_deg=slot_rotation + jitter.randint(-6, 6),
                z_index=20 + index,
                accent=_ACCENTS[index % len(_ACCENTS)],
                tape_offset_pct=18 + jitter.randint(0, 54),
                animation_delay_ms=index * 90,
            )
        )
    return cards


def _build_trash_cards(db: Session) -> list[TrashPhotoCard]:
    settings = get_settings()
    cards: list[TrashPhotoCard] = []
    for photo in list_trashed_photos(db, limit=settings.TRASH_PREVIEW_LIMIT):
        tossed_at_label = "刚刚丢进去"
        if photo.tossed_at is not None:
            tossed_at_label = photo.tossed_at.astimezone().strftime("%m-%d %H:%M")
        cards.append(
            TrashPhotoCard(
                id=photo.id,
                title=photo.title,
                caption=photo.caption,
                image_url=resolve_image_url(settings, photo.oss_path),
                tossed_at_label=tossed_at_label,
            )
        )
    return cards


def build_dashboard_snapshot(db: Session, *, display_date: date | None = None) -> DashboardSnapshot:
    target_date = display_date or date.today()
    sync_missing_photos_from_oss(db)
    ensure_daily_selection(db, display_date=target_date)

    total_photos = count_photos(db)
    trashed_photos = count_trashed_photos(db)
    desk_cards = _build_desk_cards(db, display_date=target_date)
    trash_cards = _build_trash_cards(db)
    daily_limit = _daily_limit()

    summary = [
        SummaryMetric(label="照片总数", value=str(total_photos), hint="当前照片池里登记的全部 OSS 引用"),
        SummaryMetric(label="今天上桌", value=str(len(desk_cards)), hint="今天这批拍立得会保持稳定，除非你手动丢进垃圾桶"),
        SummaryMetric(label="垃圾桶", value=str(trashed_photos), hint="被你临时嫌弃、但还能随时捡回的照片"),
        SummaryMetric(label="每日配额", value=str(daily_limit), hint="每天自动随机抽到桌面上的目标张数"),
    ]

    return DashboardSnapshot(
        source="Aliyun OSS",
        display_date=target_date.isoformat(),
        daily_limit=daily_limit,
        summary=summary,
        desk_cards=desk_cards,
        trash_cards=trash_cards,
        empty_desk_message="桌子还是空的。先录入几张 OSS 照片，系统明天起就会自动帮你抽图上桌。",
        empty_trash_message="垃圾桶现在是空的，今天暂时没有被你扔掉的照片。",
        add_photo_hint="可以直接填完整公网 URL；如果你只想填对象 key，请在 .env 里配置 ALIYUN_OSS_PUBLIC_BASE_URL。",
        tips=[
            "系统只保存 OSS 引用，不在本项目落地原始照片文件。",
            "每天会固定随机挑出一批照片，保证当天桌面展示稳定。",
            "扔进垃圾桶不会删除照片记录，只是暂时移出桌面。",
        ],
    )
