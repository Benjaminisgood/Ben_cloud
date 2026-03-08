from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from benjournal_api.core.config import get_settings


@dataclass
class StoredObject:
    provider: str
    key: str
    url: str


class StorageError(RuntimeError):
    pass


def upload_daily_audio(local_path: Path, *, entry_date: date) -> StoredObject:
    settings = get_settings()
    provider = settings.STORAGE_PROVIDER.strip().lower()
    if provider == "local":
        return _store_locally(local_path, entry_date=entry_date)
    if provider == "aliyun_oss":
        return _store_in_aliyun_oss(local_path, entry_date=entry_date)
    raise StorageError(f"不支持的存储提供方: {settings.STORAGE_PROVIDER}")


def _object_key(entry_date: date, suffix: str) -> str:
    settings = get_settings()
    return (
        f"{settings.OSS_OBJECT_PREFIX.strip('/')}/"
        f"{entry_date.year:04d}/{entry_date.month:02d}/{entry_date.isoformat()}/"
        f"{entry_date.isoformat()}-merged{suffix}"
    )


def _store_locally(local_path: Path, *, entry_date: date) -> StoredObject:
    settings = get_settings()
    key = _object_key(entry_date, local_path.suffix.lower())
    target = settings.LOCAL_ARCHIVE_DIR / key
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(local_path, target)
    return StoredObject(
        provider="local",
        key=key,
        url=f"local://{key}",
    )


def _store_in_aliyun_oss(local_path: Path, *, entry_date: date) -> StoredObject:
    settings = get_settings()
    required = {
        "ALIYUN_OSS_ENDPOINT": settings.ALIYUN_OSS_ENDPOINT,
        "ALIYUN_OSS_BUCKET": settings.ALIYUN_OSS_BUCKET,
        "ALIYUN_OSS_ACCESS_KEY_ID": settings.ALIYUN_OSS_ACCESS_KEY_ID,
        "ALIYUN_OSS_ACCESS_KEY_SECRET": settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
    }
    missing = [name for name, value in required.items() if not value.strip()]
    if missing:
        raise StorageError("Aliyun OSS 配置缺失: " + ", ".join(missing))

    try:
        import oss2  # type: ignore
    except ImportError as exc:
        raise StorageError("未安装 oss2，无法上传到阿里云 OSS。") from exc

    auth = oss2.Auth(settings.ALIYUN_OSS_ACCESS_KEY_ID, settings.ALIYUN_OSS_ACCESS_KEY_SECRET)
    endpoint = settings.ALIYUN_OSS_ENDPOINT
    bucket = oss2.Bucket(auth, endpoint, settings.ALIYUN_OSS_BUCKET)
    key = _object_key(entry_date, local_path.suffix.lower())
    bucket.put_object_from_file(key, str(local_path))

    public_base = settings.ALIYUN_OSS_PUBLIC_BASE_URL.strip().rstrip("/")
    if public_base:
        url = f"{public_base}/{key}"
    else:
        url = f"oss://{settings.ALIYUN_OSS_BUCKET}/{key}"
    return StoredObject(provider="aliyun_oss", key=key, url=url)
