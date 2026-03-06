from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from .common import TimestampMixin, utcnow_naive


class DailyDigestJob(Base, TimestampMixin):
    __tablename__ = "daily_digest_job"

    id = Column(Integer, primary_key=True)
    day = Column(Date, nullable=False, index=True)
    timezone = Column(String(64), nullable=False, default="Asia/Shanghai")
    status = Column(String(16), nullable=False, default="running")
    started_at = Column(DateTime, nullable=False, default=utcnow_naive)
    finished_at = Column(DateTime, nullable=True)
    error = Column(Text, nullable=False, default="")
    blog_asset_id = Column(Integer, ForeignKey("generated_asset.id"), nullable=True)
    podcast_asset_id = Column(Integer, ForeignKey("generated_asset.id"), nullable=True)
    poster_asset_id = Column(Integer, ForeignKey("generated_asset.id"), nullable=True)
    blog_asset = relationship("GeneratedAsset", foreign_keys=[blog_asset_id], lazy="joined")
    podcast_asset = relationship("GeneratedAsset", foreign_keys=[podcast_asset_id], lazy="joined")
    poster_asset = relationship("GeneratedAsset", foreign_keys=[poster_asset_id], lazy="joined")
