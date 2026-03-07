from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from settings import settings

try:  # pragma: no cover - optional runtime dependency
    import oss2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    oss2 = None


class StorageError(RuntimeError):
    pass


class StorageBackend:
    def read_bytes(self, key: str) -> bytes | None:
        raw = self.read_text(key)
        if raw is None:
            return None
        return raw.encode("utf-8")

    def write_bytes(self, key: str, content: bytes) -> None:
        self.write_text(key, content.decode("utf-8"))

    def read_text(self, key: str) -> str | None:
        raise NotImplementedError

    def write_text(self, key: str, content: str) -> None:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError

    def read_json(self, key: str, default: Any) -> Any:
        raw = self.read_text(key)
        if raw is None:
            return default
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return default

    def write_json(self, key: str, payload: Any) -> None:
        self.write_text(
            key,
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        )


class LocalStorageBackend(StorageBackend):
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        cleaned = key.strip().strip("/")
        return self.root_dir / cleaned

    def read_text(self, key: str) -> str | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")

    def read_bytes(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.exists():
            return None
        return path.read_bytes()

    def write_text(self, key: str, content: str) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(path)

    def write_bytes(self, key: str, content: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(content)
        tmp.replace(path)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class AliyunOSSStorageBackend(StorageBackend):
    def __init__(
        self,
        *,
        endpoint: str,
        access_key_id: str,
        access_key_secret: str,
        bucket_name: str,
        prefix: str,
    ) -> None:
        if oss2 is None:
            raise StorageError(
                "未安装 oss2，无法启用阿里云 OSS 存储。请先执行依赖安装。"
            )

        endpoint = endpoint.strip()
        bucket_name = bucket_name.strip()
        if not endpoint or not bucket_name:
            raise StorageError("OSS 配置不完整，缺少 endpoint 或 bucket")

        auth = oss2.Auth(access_key_id.strip(), access_key_secret.strip())
        self.bucket = oss2.Bucket(auth, f"https://{endpoint}", bucket_name)
        self.prefix = prefix.strip().strip("/")

    def _key(self, key: str) -> str:
        cleaned = key.strip().strip("/")
        if not self.prefix:
            return cleaned
        return f"{self.prefix}/{cleaned}"

    def read_text(self, key: str) -> str | None:
        raw = self.read_bytes(key)
        if raw is None:
            return None
        return raw.decode("utf-8")

    def read_bytes(self, key: str) -> bytes | None:
        target = self._key(key)
        try:
            result = self.bucket.get_object(target)
        except Exception as exc:  # pragma: no cover - remote error path
            status = getattr(exc, "status", None)
            if status == 404:
                return None
            details = getattr(exc, "details", "") or str(exc)
            if "NoSuchKey" in details:
                return None
            raise StorageError(f"OSS 读取失败: {target}") from exc
        return result.read()

    def write_text(self, key: str, content: str) -> None:
        self.write_bytes(key, content.encode("utf-8"))

    def write_bytes(self, key: str, content: bytes) -> None:
        target = self._key(key)
        try:
            self.bucket.put_object(target, content)
        except Exception as exc:  # pragma: no cover - remote error path
            raise StorageError(f"OSS 写入失败: {target}") from exc

    def delete(self, key: str) -> None:
        target = self._key(key)
        try:
            self.bucket.delete_object(target)
        except Exception as exc:  # pragma: no cover - remote error path
            raise StorageError(f"OSS 删除失败: {target}") from exc


class MirrorStorageBackend(StorageBackend):
    def __init__(self, primary: StorageBackend, secondary: StorageBackend) -> None:
        self.primary = primary
        self.secondary = secondary

    def read_text(self, key: str) -> str | None:
        primary_value = self.primary.read_text(key)
        if primary_value is not None:
            return primary_value
        fallback = self.secondary.read_text(key)
        if fallback is not None:
            self.primary.write_text(key, fallback)
        return fallback

    def read_bytes(self, key: str) -> bytes | None:
        primary_value = self.primary.read_bytes(key)
        if primary_value is not None:
            return primary_value
        fallback = self.secondary.read_bytes(key)
        if fallback is not None:
            self.primary.write_bytes(key, fallback)
        return fallback

    def write_text(self, key: str, content: str) -> None:
        self.primary.write_text(key, content)
        self.secondary.write_text(key, content)

    def write_bytes(self, key: str, content: bytes) -> None:
        self.primary.write_bytes(key, content)
        self.secondary.write_bytes(key, content)

    def delete(self, key: str) -> None:
        self.primary.delete(key)
        self.secondary.delete(key)


def build_labdocs_storage() -> StorageBackend:
    local_backend = LocalStorageBackend(Path(settings.LABDOCS_LOCAL_ROOT))
    if settings.LABDOCS_STORAGE_BACKEND == "local":
        return local_backend

    return AliyunOSSStorageBackend(
        endpoint=settings.ALIYUN_OSS_ENDPOINT,
        access_key_id=settings.ALIYUN_OSS_ACCESS_KEY_ID,
        access_key_secret=settings.ALIYUN_OSS_ACCESS_KEY_SECRET,
        bucket_name=settings.ALIYUN_OSS_BUCKET,
        prefix=settings.LABDOCS_STORAGE_PREFIX,
    )
