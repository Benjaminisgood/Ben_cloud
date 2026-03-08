from __future__ import annotations

from datetime import date

from sqlalchemy.orm import Session

from benjournal_api.repositories.journal_days_repo import get_day_totals, list_recent_days
from benjournal_api.schemas.dashboard import DashboardSnapshot, SummaryMetric
from benjournal_api.services.journal_days import get_journal_day_detail, serialize_list_item


def build_dashboard_snapshot(db: Session, *, selected_date: date | None = None) -> DashboardSnapshot:
    current_date = selected_date or date.today()
    recent_days = list_recent_days(db, limit=10)
    day_count, total_segments = get_day_totals(db)
    latest_update = recent_days[0].updated_at.strftime("%Y-%m-%d %H:%M") if recent_days else "暂无"
    selected_day = get_journal_day_detail(db, entry_date=current_date)

    summary = [
        SummaryMetric(label="已记录天数", value=str(day_count), hint="至少有一条文本或语音的日期数量。"),
        SummaryMetric(label="音频片段", value=str(total_segments), hint="所有按日归档的录音段总数。"),
        SummaryMetric(label="当前日期", value=current_date.isoformat(), hint="手动切换日期后再录音或补文本。"),
        SummaryMetric(label="最近更新", value=latest_update, hint="方便确认今天的日志是否已经同步。"),
    ]
    return DashboardSnapshot(
        selected_date=current_date.isoformat(),
        selected_day=selected_day,
        recent_days=[serialize_list_item(item) for item in recent_days],
        summary=summary,
    )
