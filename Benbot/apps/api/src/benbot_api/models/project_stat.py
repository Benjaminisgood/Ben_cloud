from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Column, Date, DateTime, Integer, String, UniqueConstraint

from ..db.base import Base


class ProjectHealth(Base):
    """Stores the latest health check result per project."""
    __tablename__ = "project_health"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(16), nullable=False, default="unknown")  # "up", "down", "unknown"
    response_ms = Column(Integer, nullable=True)
    last_checked = Column(DateTime, nullable=True)


class ProjectClick(Base):
    """Daily click counter per project."""
    __tablename__ = "project_click"

    id = Column(Integer, primary_key=True)
    project_id = Column(String(64), nullable=False, index=True)
    click_date = Column(Date, nullable=False, default=date.today)
    count = Column(Integer, nullable=False, default=0)

    __table_args__ = (UniqueConstraint("project_id", "click_date", name="uq_project_click_date"),)
