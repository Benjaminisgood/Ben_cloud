"""房间媒体服务"""
from __future__ import annotations

import mimetypes
import os
import uuid
from pathlib import Path
from typing import List, Optional

from sqlalchemy.orm import Session

from ..models.common import utcnow_naive
from ..models.property import Property
from ..models.property_media import PropertyMedia
from ..utils.oss import delete_media_file, upload_media_file
from .errors import ServiceError, ServiceErrorCode


def _generate_oss_key(property_id: int, filename: str) -> str:
    """生成 OSS 存储路径"""
    ext = Path(filename).suffix.lower()
    if not ext:
        ext = ".bin"
    
    # 格式：benome/properties/{property_id}/{uuid}{ext}
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"benome/properties/{property_id}/{unique_name}"


def _get_mime_type(file_path: str) -> str:
    """获取文件 MIME 类型"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"


def _is_video_file(file_path: str) -> bool:
    """判断是否为视频文件"""
    mime_type = _get_mime_type(file_path)
    return mime_type.startswith("video/")


def upload_property_media(
    db: Session,
    property_id: int,
    file_path: str,
    title: Optional[str] = None,
    description: Optional[str] = None,
    is_cover: bool = False,
) -> PropertyMedia:
    """
    上传房间媒体文件
    
    Args:
        db: 数据库会话
        property_id: 房间 ID
        file_path: 本地文件路径
        title: 媒体标题
        description: 媒体描述
        is_cover: 是否设为封面
        
    Returns:
        创建的媒体记录
    """
    # 验证房间是否存在
    property_obj = db.query(Property).filter(Property.id == property_id).first()
    if not property_obj:
        raise ServiceError(
            detail="房间不存在",
            status_code=404,
            code=ServiceErrorCode.NOT_FOUND,
        )
    
    # 验证文件存在
    if not os.path.exists(file_path):
        raise ServiceError(
            detail="文件不存在",
            status_code=400,
            code=ServiceErrorCode.INVALID_INPUT,
        )
    
    # 生成 OSS 路径
    filename = os.path.basename(file_path)
    oss_key = _generate_oss_key(property_id, filename)
    
    # 获取文件信息
    file_size = os.path.getsize(file_path)
    mime_type = _get_mime_type(file_path)
    media_type = "video" if _is_video_file(file_path) else "image"
    
    # 上传到 OSS
    try:
        public_url = upload_media_file(file_path, oss_key, content_type=mime_type)
    except Exception as e:
        raise ServiceError(
            detail=f"上传失败：{str(e)}",
            status_code=500,
            code=ServiceErrorCode.INTERNAL_ERROR,
        )
    
    # 如果设为封面，取消其他封面
    if is_cover:
        db.query(PropertyMedia).filter(
            PropertyMedia.property_id == property_id,
            PropertyMedia.is_cover == True
        ).update({"is_cover": False})
    
    # 创建数据库记录
    media = PropertyMedia(
        property_id=property_id,
        media_type=media_type,
        oss_key=oss_key,
        public_url=public_url,
        file_size=file_size,
        mime_type=mime_type,
        title=title or "",
        description=description or "",
        is_cover=is_cover,
        is_active=True,
        sort_order=0,
    )
    
    db.add(media)
    db.commit()
    db.refresh(media)
    
    return media


def get_property_media_list(
    db: Session,
    property_id: int,
    include_inactive: bool = False,
) -> List[PropertyMedia]:
    """获取房间的媒体列表"""
    query = db.query(PropertyMedia).filter(
        PropertyMedia.property_id == property_id
    )
    
    if not include_inactive:
        query = query.filter(PropertyMedia.is_active == True)
    
    # 按排序和创建时间排序
    query = query.order_by(PropertyMedia.sort_order, PropertyMedia.created_at)
    
    return query.all()


def get_property_media(
    db: Session,
    media_id: int,
) -> PropertyMedia:
    """获取单个媒体记录"""
    media = db.query(PropertyMedia).filter(PropertyMedia.id == media_id).first()
    if not media:
        raise ServiceError(
            detail="媒体记录不存在",
            status_code=404,
            code=ServiceErrorCode.NOT_FOUND,
        )
    return media


def update_property_media(
    db: Session,
    media_id: int,
    title: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
    is_cover: Optional[bool] = None,
    is_active: Optional[bool] = None,
) -> PropertyMedia:
    """更新媒体记录"""
    media = get_property_media(db, media_id)
    
    # 如果设为封面，取消其他封面
    if is_cover and not media.is_cover:
        db.query(PropertyMedia).filter(
            PropertyMedia.property_id == media.property_id,
            PropertyMedia.is_cover == True,
            PropertyMedia.id != media_id
        ).update({"is_cover": False})
    
    # 更新字段
    if title is not None:
        media.title = title
    if description is not None:
        media.description = description
    if sort_order is not None:
        media.sort_order = sort_order
    if is_cover is not None:
        media.is_cover = is_cover
    if is_active is not None:
        media.is_active = is_active
    
    media.updated_at = utcnow_naive()
    
    db.commit()
    db.refresh(media)
    return media


def delete_property_media(
    db: Session,
    media_id: int,
) -> bool:
    """删除媒体记录（包括 OSS 文件）"""
    media = get_property_media(db, media_id)
    
    # 删除 OSS 文件
    try:
        delete_media_file(media.oss_key)
    except Exception:
        pass  # OSS 删除失败不影响数据库删除
    
    # 删除数据库记录
    db.delete(media)
    db.commit()
    
    return True


def set_media_cover(
    db: Session,
    property_id: int,
    media_id: int,
) -> PropertyMedia:
    """设置房间封面"""
    # 验证媒体属于该房间
    media = db.query(PropertyMedia).filter(
        PropertyMedia.id == media_id,
        PropertyMedia.property_id == property_id
    ).first()
    
    if not media:
        raise ServiceError(
            detail="媒体记录不存在或不属于该房间",
            status_code=404,
            code=ServiceErrorCode.NOT_FOUND,
        )
    
    # 取消其他封面
    db.query(PropertyMedia).filter(
        PropertyMedia.property_id == property_id,
        PropertyMedia.is_cover == True
    ).update({"is_cover": False})
    
    # 设置新封面
    media.is_cover = True
    media.updated_at = utcnow_naive()
    
    db.commit()
    db.refresh(media)
    
    return media
