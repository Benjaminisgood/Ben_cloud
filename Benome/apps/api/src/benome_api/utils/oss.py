"""Benome OSS 工具 - 用于房间媒体文件上传和管理"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import oss2

from ..core.config import get_settings

logger = logging.getLogger(__name__)


def _has_oss_config() -> bool:
    """检查是否配置了 OSS"""
    s = get_settings()
    return bool(
        s.ALIYUN_OSS_ENDPOINT 
        and s.ALIYUN_OSS_ACCESS_KEY_ID 
        and s.ALIYUN_OSS_ACCESS_KEY_SECRET 
        and s.ALIYUN_OSS_BUCKET
    )


def _get_bucket():
    """获取 OSS Bucket 实例"""
    s = get_settings()
    auth = oss2.Auth(s.ALIYUN_OSS_ACCESS_KEY_ID, s.ALIYUN_OSS_ACCESS_KEY_SECRET)
    return oss2.Bucket(auth, s.ALIYUN_OSS_ENDPOINT, s.ALIYUN_OSS_BUCKET)


def upload_media_file(
    file_path: str,
    oss_key: str,
    content_type: Optional[str] = None
) -> str:
    """
    上传媒体文件到 OSS
    
    Args:
        file_path: 本地文件路径
        oss_key: OSS 存储路径（如 benome/properties/123/image.jpg）
        content_type: MIME 类型
        
    Returns:
        公开访问 URL
    """
    s = get_settings()
    
    if not _has_oss_config():
        logger.warning("OSS 未配置，无法上传文件")
        raise ValueError("OSS 配置缺失")
    
    try:
        bucket = _get_bucket()
        headers = {
            "Content-Type": content_type,
            "x-oss-object-acl": "public-read"  # 设置文件为公共读
        } if content_type else {"x-oss-object-acl": "public-read"}
        bucket.put_object_from_file(oss_key, file_path, headers=headers)
        
        # 生成公开 URL
        public_url = f"https://{s.ALIYUN_OSS_BUCKET}.{s.ALIYUN_OSS_ENDPOINT.split('//')[-1]}/{oss_key}"
        return public_url
        
    except Exception as e:
        logger.error(f"OSS 上传失败：{e}")
        raise


def delete_media_file(oss_key: str) -> bool:
    """
    删除 OSS 上的媒体文件
    
    Args:
        oss_key: OSS 存储路径
        
    Returns:
        是否成功删除
    """
    if not _has_oss_config():
        return False
    
    try:
        bucket = _get_bucket()
        bucket.delete_object(oss_key)
        return True
    except Exception as e:
        logger.error(f"OSS 删除失败：{e}")
        return False


def generate_upload_url(
    oss_key: str,
    content_type: str,
    expires: int = 900
) -> str:
    """
    生成签名上传 URL（用于前端直传）
    
    Args:
        oss_key: OSS 存储路径
        content_type: MIME 类型
        expires: 过期时间（秒）
        
    Returns:
        签名上传 URL
    """
    if not _has_oss_config():
        return ""
    
    try:
        bucket = _get_bucket()
        headers = {"Content-Type": content_type}
        url = bucket.sign_url("PUT", oss_key, expires, headers=headers)
        return url
    except Exception as e:
        logger.error(f"生成上传 URL 失败：{e}")
        return ""


def get_public_url(oss_key: str, expires: int = 86400 * 365) -> str:
    """
    获取媒体文件的公开访问 URL（带签名）
    
    Args:
        oss_key: OSS 存储路径
        expires: 签名过期时间（秒），默认 1 年
        
    Returns:
        公开访问 URL（带签名）
    """
    s = get_settings()
    if not _has_oss_config():
        return ""
    
    try:
        bucket = _get_bucket()
        # 生成带签名的 URL，有效期 1 年
        # slash_safe=True 确保路径中的斜杠不会被编码
        url = bucket.sign_url('GET', oss_key, expires, slash_safe=True)
        logger.debug(f"生成签名 URL: {url[:80]}...")
        return url
    except Exception as e:
        logger.error(f"生成签名 URL 失败：{e}")
        # 降级返回普通 URL（可能需要 Bucket 为公共读）
        endpoint = s.ALIYUN_OSS_ENDPOINT.split('//')[-1]
        return f"https://{s.ALIYUN_OSS_BUCKET}.{endpoint}/{oss_key}"
