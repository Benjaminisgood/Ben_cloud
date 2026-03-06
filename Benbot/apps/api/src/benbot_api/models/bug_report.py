from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from ..db.base import Base


class BugReport(Base):
    __tablename__ = "bug_report"

    id = Column(Integer, primary_key=True)
    reporter_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String(32), nullable=False, default="pending")  # pending | approved | rejected
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    approved_at = Column(DateTime, nullable=True)
    repaired = Column(Integer, default=0)  # 0: not repaired, 1: repaired by nanobot
    verified = Column(Integer, default=0)  # 0: not verified, 1: verified by admin

    __table_args__ = (
        Index("ix_bug_report_status_approved_at", "status", "approved_at"),
    )
