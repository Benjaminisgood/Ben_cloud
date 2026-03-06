from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PropertyMediaBase(BaseModel):
    media_type: str = Field(..., description="媒体类型：image, video")
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    sort_order: int = Field(default=0)
    is_cover: bool = Field(default=False)


class PropertyMediaCreateRequest(PropertyMediaBase):
    """创建媒体请求"""
    pass


class PropertyMediaUpdateRequest(BaseModel):
    """更新媒体请求"""
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_cover: Optional[bool] = None
    is_active: Optional[bool] = None


class PropertyMediaOut(PropertyMediaBase):
    """媒体响应"""
    id: int
    property_id: int
    oss_key: str
    public_url: Optional[str]
    file_size: Optional[int]
    mime_type: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PropertyMediaUploadResponse(BaseModel):
    """上传响应"""
    id: int
    property_id: int
    oss_key: str
    public_url: str
    media_type: str
    file_size: int
    mime_type: str
