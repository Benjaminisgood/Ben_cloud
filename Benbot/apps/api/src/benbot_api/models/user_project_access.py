from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint

from ..db.base import Base


class UserProjectAccess(Base):
    """Per-user allowlist for portal project visibility."""

    __tablename__ = "user_project_access"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    project_id = Column(String(64), nullable=False, index=True)
    granted_by = Column(String(80), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("user_id", "project_id", name="uq_user_project_access_user_project"),
        Index("ix_user_project_access_user_project", "user_id", "project_id"),
    )
