from __future__ import annotations

from sqlalchemy import Boolean, Column, Date, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from ..db.base import Base
from .common import TimestampMixin


class GeneratedAsset(Base, TimestampMixin):
    __tablename__ = "generated_asset"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False, index=True)
    user = relationship("User", backref="generated_assets", lazy="joined")
    kind = Column(String(32), nullable=False)
    title = Column(String(255), nullable=False, default="")
    provider = Column(String(64), nullable=False, default="")
    model = Column(String(128), nullable=False, default="")
    visibility = Column(String(16), nullable=False, default="private")
    status = Column(String(16), nullable=False, default="ready")
    is_daily_digest = Column(Boolean, nullable=False, default=False)
    source_day = Column(Date, nullable=True, index=True)
    content_type = Column(String(255), nullable=False, default="")
    ext = Column(String(16), nullable=False, default="")
    file_type = Column(String(16), nullable=False, default="file")
    size_bytes = Column(Integer, nullable=False, default=0)
    oss_key = Column(String(512), nullable=False, default="")
    sha256 = Column(String(64), nullable=False, default="")
    source_filters_json = Column(Text, nullable=False, default="{}")


Index("ix_generated_asset_user_created", GeneratedAsset.user_id, GeneratedAsset.created_at)
Index(
    "ix_generated_asset_public_day_created",
    GeneratedAsset.visibility,
    GeneratedAsset.source_day,
    GeneratedAsset.created_at,
)

