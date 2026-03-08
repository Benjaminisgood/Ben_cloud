from __future__ import annotations

import random
from datetime import date
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..repositories.records_repo import (
    count_records,
    count_trashed_records,
    list_selected_records,
    list_trashed_records,
)
from ..schemas.dashboard import DashboardSnapshot, DeskVinylCard, SummaryMetric, TrashVinylCard, TurntableNowPlaying
from .oss_sync import sync_missing_records_from_oss
from .records import ensure_daily_selection, resolve_audio_url

_DECK_SLOTS: list[tuple[int, int, int]] = [
    (8, 90, -14),
    (24, 48, 10),
    (43, 120, -8),
    (61, 54, 12),
    (76, 112, -11),
    (18, 210, 7),
    (37, 252, -10),
    (58, 218, 5),
]
_LABEL_TONES = ["#d96f3d", "#c4a44d", "#5f8f83", "#9b5de5", "#e56b9d", "#5c7cfa"]


def _short_source_label(oss_path: str) -> str:
    parsed = urlparse(oss_path)
    if parsed.netloc:
        return parsed.netloc
    parts = [part for part in oss_path.split("/") if part]
    if not parts:
        return "OSS"
    return "/".join(parts[-2:])


def _build_deck_cards(
    db: Session,
    *,
    display_date: date,
    active_record_id: int | None,
) -> tuple[list[DeskVinylCard], TurntableNowPlaying | None]:
    settings = get_settings()
    records = list_selected_records(db, display_date=display_date, include_trashed=False)
    ordered = sorted(records, key=lambda record: record.id)
    random.Random(f"benvinyl:deck:{display_date.isoformat()}").shuffle(ordered)

    active_id = active_record_id if any(record.id == active_record_id for record in ordered) else None
    if active_id is None and ordered:
        active_id = ordered[0].id

    cards: list[DeskVinylCard] = []
    now_playing: TurntableNowPlaying | None = None
    for index, record in enumerate(ordered):
        slot_x, slot_y, slot_rotation = _DECK_SLOTS[index % len(_DECK_SLOTS)]
        jitter = random.Random(f"benvinyl:card:{display_date.isoformat()}:{record.id}")
        audio_url = resolve_audio_url(settings, record.oss_path)
        is_active = record.id == active_id
        cards.append(
            DeskVinylCard(
                id=record.id,
                title=record.title,
                note=record.note,
                audio_url=audio_url,
                source_label=_short_source_label(record.oss_path),
                x_pct=max(4, min(79, slot_x + jitter.randint(-4, 4))),
                y_px=max(28, slot_y + jitter.randint(-18, 18)),
                rotation_deg=slot_rotation + jitter.randint(-6, 6),
                z_index=30 + index,
                label_tone=_LABEL_TONES[index % len(_LABEL_TONES)],
                animation_delay_ms=index * 90,
                is_active=is_active,
            )
        )
        if is_active:
            now_playing = TurntableNowPlaying(
                id=record.id,
                title=record.title,
                note=record.note,
                audio_url=audio_url,
                source_label=_short_source_label(record.oss_path),
            )

    return cards, now_playing


def _build_trash_cards(db: Session) -> list[TrashVinylCard]:
    settings = get_settings()
    cards: list[TrashVinylCard] = []
    for record in list_trashed_records(db, limit=settings.TRASH_PREVIEW_LIMIT):
        tossed_at_label = "刚刚丢进去"
        if record.tossed_at is not None:
            tossed_at_label = record.tossed_at.astimezone().strftime("%m-%d %H:%M")
        cards.append(
            TrashVinylCard(
                id=record.id,
                title=record.title,
                note=record.note,
                tossed_at_label=tossed_at_label,
            )
        )
    return cards


def build_dashboard_snapshot(
    db: Session,
    *,
    display_date: date | None = None,
    active_record_id: int | None = None,
) -> DashboardSnapshot:
    target_date = display_date or date.today()
    sync_missing_records_from_oss(db)
    ensure_daily_selection(db, display_date=target_date)

    deck_cards, now_playing = _build_deck_cards(db, display_date=target_date, active_record_id=active_record_id)
    trash_cards = _build_trash_cards(db)
    daily_limit = max(get_settings().DAILY_RECORD_COUNT, 1)

    summary = [
        SummaryMetric(label="唱片总数", value=str(count_records(db)), hint="当前唱片池里登记的全部 OSS 音频引用"),
        SummaryMetric(label="今日节目", value=str(len(deck_cards)), hint="今天桌面上已经开播的固定节目数"),
        SummaryMetric(label="垃圾桶", value=str(count_trashed_records(db)), hint="被你临时下架、但还能随时捡回的唱片"),
        SummaryMetric(label="每日配额", value=str(daily_limit), hint="每天自动随机上线的目标节目数"),
    ]

    return DashboardSnapshot(
        source="Aliyun OSS",
        display_date=target_date.isoformat(),
        daily_limit=daily_limit,
        summary=summary,
        now_playing=now_playing,
        deck_cards=deck_cards,
        trash_cards=trash_cards,
        empty_deck_message="唱片机今天还没有节目。先录入几张 OSS 音频，系统会自动把它们编成每日节目单。",
        empty_trash_message="垃圾桶还是空的，今天暂时没有被你下架的唱片。",
        add_record_hint="可以直接填完整公网 URL；如果只填对象 key，请在 .env 里配置 ALIYUN_OSS_PUBLIC_BASE_URL。",
        tips=[
            "系统只保存 OSS 引用，不在本项目落地原始音频文件。",
            "每天会固定随机挑出一批节目，保证当天的唱片堆稳定。",
            "拖进垃圾桶不会删除唱片，只是把它临时从公开节目中拿下。",
        ],
    )
