from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, Text, DateTime
from datetime import datetime

from ..db.base import Base


class PropertyMedia(Base):
    """房间媒体资源（图片/视频）"""
    __tablename__ = "property_media"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 媒体类型：image, video
    media_type = Column(String(20), nullable=False, default="image")
    
    # OSS 存储路径
    oss_key = Column(String(512), nullable=False, unique=True)
    
    # 公开访问 URL（可选，用于缓存）
    public_url = Column(String(1024), nullable=True)
    
    # 文件信息
    file_size = Column(Integer, nullable=True)  # 字节
    mime_type = Column(String(100), nullable=True)  # 如 image/jpeg, video/mp4
    
    # 元数据
    title = Column(String(200), nullable=True, default="")
    description = Column(Text, nullable=True, default="")
    
    # 排序和展示
    sort_order = Column(Integer, nullable=False, default=0)
    is_cover = Column(Boolean, nullable=False, default=False)  # 是否封面
    is_active = Column(Boolean, nullable=False, default=True)
    
    # 时间戳
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
