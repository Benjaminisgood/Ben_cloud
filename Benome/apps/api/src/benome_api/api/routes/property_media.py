"""房间媒体管理 API"""
from __future__ import annotations

import os
import tempfile
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ...models.user import User
from ...schemas.property_media import (
    PropertyMediaCreateRequest,
    PropertyMediaOut,
    PropertyMediaUpdateRequest,
    PropertyMediaUploadResponse,
)
from ...services.property_media import (
    delete_property_media,
    get_property_media,
    get_property_media_list,
    set_media_cover,
    update_property_media,
    upload_property_media,
)
from ...services.errors import ServiceError
from ..deps import get_current_admin, get_db

router = APIRouter(tags=["property-media"])


@router.get("/properties/{property_id}/media", response_model=List[PropertyMediaOut])
def list_property_media(
    property_id: int,
    db: Session = Depends(get_db),
):
    """获取房间的媒体列表"""
    try:
        media_list = get_property_media_list(db, property_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return media_list


@router.post(
    "/properties/{property_id}/media/upload",
    response_model=PropertyMediaUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_media(
    property_id: int,
    file: UploadFile = File(...),
    title: str = Form(None),
    description: str = Form(None),
    is_cover: bool = Form(False),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    上传房间媒体文件
    
    - 支持图片和视频上传
    - 自动上传到阿里云 OSS
    - 返回公开访问 URL
    """
    # 验证文件类型
    allowed_types = [
        "image/jpeg", "image/png", "image/gif", "image/webp",
        "video/mp4", "video/quicktime", "video/x-msvideo"
    ]
    
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型：{file.content_type}。支持的类型：{', '.join(allowed_types)}"
        )
    
    # 验证文件大小（最大 500MB）
    max_size = 500 * 1024 * 1024  # 500MB
    content = file.file.read()
    if len(content) > max_size:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制（{max_size // 1024 // 1024}MB）"
        )
    
    # 保存临时文件
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # 上传媒体
        media = upload_property_media(
            db=db,
            property_id=property_id,
            file_path=tmp_path,
            title=title,
            description=description,
            is_cover=is_cover,
        )
        
        return PropertyMediaUploadResponse(
            id=media.id,
            property_id=media.property_id,
            oss_key=media.oss_key,
            public_url=media.public_url,
            media_type=media.media_type,
            file_size=media.file_size,
            mime_type=media.mime_type,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
        
    finally:
        # 清理临时文件
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


@router.get("/media/{media_id}", response_model=PropertyMediaOut)
def get_media_detail(
    media_id: int,
    db: Session = Depends(get_db),
):
    """获取媒体详情"""
    try:
        media = get_property_media(db, media_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return media


@router.patch("/media/{media_id}", response_model=PropertyMediaOut)
def update_media(
    media_id: int,
    payload: PropertyMediaUpdateRequest,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """更新媒体信息"""
    try:
        media = update_property_media(
            db=db,
            media_id=media_id,
            title=payload.title,
            description=payload.description,
            sort_order=payload.sort_order,
            is_cover=payload.is_cover,
            is_active=payload.is_active,
        )
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return media


@router.delete("/media/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_media(
    media_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """删除媒体记录"""
    try:
        delete_property_media(db, media_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None


@router.post("/properties/{property_id}/media/{media_id}/set-cover", response_model=PropertyMediaOut)
def set_cover(
    property_id: int,
    media_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """设置房间封面"""
    try:
        media = set_media_cover(db, property_id, media_id)
    except ServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from None
    return media
