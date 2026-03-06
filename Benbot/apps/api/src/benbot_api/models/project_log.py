from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, Index, Integer, String, Text

from ..db.base import Base


class ProjectLog(Base):
    """每个项目的运行日志与报错记录。"""

    __tablename__ = "project_log"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    level = Column(String(16), nullable=False, default="INFO")   # INFO / WARNING / ERROR
    source = Column(String(32), nullable=False, default="system")  # health_check / project_control / system
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("ix_project_log_project_created_at", "project_id", "created_at"),
    )
