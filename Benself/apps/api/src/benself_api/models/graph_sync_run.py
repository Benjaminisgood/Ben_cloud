from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from benself_api.db.base import Base


class GraphSyncRun(Base):
    __tablename__ = "graph_sync_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mode: Mapped[str] = mapped_column(String(20), default="preview")
    status: Mapped[str] = mapped_column(String(20), default="preview")
    raw_episode_count: Mapped[int] = mapped_column(Integer, default=0)
    confirmed_episode_count: Mapped[int] = mapped_column(Integer, default=0)
    backend: Mapped[str] = mapped_column(String(40), default="preview")
    message: Mapped[str] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
