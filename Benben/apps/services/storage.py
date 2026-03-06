from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path, PurePosixPath

import oss2
from fastapi import HTTPException, UploadFile, status

from ..core.config import Settings, get_settings

_ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
_ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/gif",
    "image/webp",
}
_MARKDOWN_PATH_RE = re.compile(r"^[A-Za-z0-9_\-./\u4e00-\u9fff]{1,200}\.md$")


class FileNotFoundErrorInStore(Exception):
    pass


class VersionConflictError(Exception):
    def __init__(self, *, path: str, current_version: str, current_content: str) -> None:
        self.path = path
        self.current_version = current_version
        self.current_content = current_content


@dataclass(frozen=True)
class FileSnapshot:
    path: str
    content: str
    version: str


@dataclass(frozen=True)
class SaveResult:
    path: str
    version: str
    created: bool


class OSSRepository:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
        self.bucket = oss2.Bucket(auth, settings.oss_endpoint, settings.oss_bucket_name)

    @staticmethod
    def hash_content(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def normalize_markdown_path(self, raw_path: str) -> str:
        candidate = (raw_path or "").strip()
        if not candidate:
            raise HTTPException(status_code=400, detail="文件路径不能为空")

        if "\\" in candidate:
            raise HTTPException(status_code=400, detail="文件路径非法")

        normalized = str(PurePosixPath(candidate))
        if normalized in {".", ".."}:
            raise HTTPException(status_code=400, detail="文件路径非法")

        parts = PurePosixPath(normalized).parts
        if normalized.startswith("/") or any(part in {"", ".", ".."} for part in parts):
            raise HTTPException(status_code=400, detail="文件路径非法")

        if not _MARKDOWN_PATH_RE.fullmatch(normalized):
            raise HTTPException(
                status_code=400,
                detail="仅允许 .md 文件，且路径只能包含字母、数字、中划线、下划线、斜杠与点",
            )

        return normalized

    def _key(self, rel_path: str) -> str:
        return f"{self._settings.oss_prefix}/{rel_path}"

    def list_markdown_files(self) -> list[str]:
        files: list[str] = []
        prefix = f"{self._settings.oss_prefix}/"

        for obj in oss2.ObjectIterator(self.bucket, prefix=prefix):
            if not obj.key.endswith(".md"):
                continue
            rel_path = obj.key[len(prefix) :]
            try:
                safe_rel_path = self.normalize_markdown_path(rel_path)
            except HTTPException:
                continue
            files.append(safe_rel_path)

        return sorted(files)

    def read_file(self, rel_path: str) -> FileSnapshot:
        key = self._key(rel_path)
        try:
            result = self.bucket.get_object(key)
        except oss2.exceptions.NoSuchKey as exc:
            raise FileNotFoundErrorInStore(rel_path) from exc
        content = result.read().decode("utf-8")
        return FileSnapshot(path=rel_path, content=content, version=self.hash_content(content))

    def save_file(
        self,
        rel_path: str,
        content: str,
        *,
        base_version: str | None,
        force: bool,
    ) -> SaveResult:
        created = False
        try:
            current = self.read_file(rel_path)
            if not force and base_version != current.version:
                raise VersionConflictError(
                    path=rel_path,
                    current_version=current.version,
                    current_content=current.content,
                )
        except FileNotFoundErrorInStore:
            created = True

        self.bucket.put_object(self._key(rel_path), content.encode("utf-8"))
        return SaveResult(path=rel_path, version=self.hash_content(content), created=created)

    def delete_file(self, rel_path: str) -> None:
        self.bucket.delete_object(self._key(rel_path))

    def upload_image(self, file: UploadFile) -> str:
        settings = get_settings()
        filename = file.filename or "upload"
        ext = Path(filename).suffix.lower()
        content_type = (file.content_type or "").lower()

        if ext not in _ALLOWED_IMAGE_EXTENSIONS:
            raise HTTPException(status_code=400, detail="不支持的图片扩展名")
        if content_type and content_type not in _ALLOWED_IMAGE_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="不支持的图片 MIME 类型")

        file_data = file.file.read(settings.upload_max_bytes + 1)
        if not file_data:
            raise HTTPException(status_code=400, detail="上传文件为空")
        if len(file_data) > settings.upload_max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"图片过大（最大 {settings.upload_max_bytes} 字节）",
            )

        key = (
            f"{settings.oss_prefix}/images/"
            f"{datetime.now().strftime('%Y/%m')}/{uuid.uuid4().hex}{ext}"
        )
        headers = {"Content-Type": content_type} if content_type else None
        self.bucket.put_object(key, file_data, headers=headers)
        return self.bucket.sign_url("GET", key, 315360000)


@lru_cache
def get_repository() -> OSSRepository:
    return OSSRepository(get_settings())
