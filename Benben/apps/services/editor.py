from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, UploadFile, status

from ..core.config import get_settings
from .audit import write_audit_log
from .rate_limit import SlidingWindowRateLimiter
from .storage import (
    FileNotFoundErrorInStore,
    FileSnapshot,
    OSSRepository,
    SaveResult,
    VersionConflictError,
)


@dataclass(frozen=True)
class EditorPrincipal:
    username: str
    role: str
    ip: str
    request_id: str


_upload_rate_limiter = SlidingWindowRateLimiter()


def _principal_from_request(request: Request, user: dict[str, str]) -> EditorPrincipal:
    request_id = str(getattr(request.state, "request_id", "") or "").strip() or "unknown"
    return EditorPrincipal(
        username=user["username"],
        role=user["role"],
        ip=(request.client.host if request.client else "unknown"),
        request_id=request_id,
    )


def _enforce_markdown_size(content: str) -> None:
    settings = get_settings()
    size = len(content.encode("utf-8"))
    if size > settings.markdown_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Markdown 内容过大（最大 {settings.markdown_max_bytes} 字节）",
        )


def list_files(repo: OSSRepository, *, user: dict[str, str], request: Request) -> list[str]:
    principal = _principal_from_request(request, user)
    files = repo.list_markdown_files()
    write_audit_log(
        action="list_files",
        user=principal.username,
        role=principal.role,
        ip=principal.ip,
        target="*",
        ok=True,
        request_id=principal.request_id,
        extra={"count": len(files)},
    )
    return files


def read_file(repo: OSSRepository, *, path: str, user: dict[str, str], request: Request) -> FileSnapshot:
    principal = _principal_from_request(request, user)
    safe_path = repo.normalize_markdown_path(path)
    try:
        snapshot = repo.read_file(safe_path)
    except FileNotFoundErrorInStore as exc:
        write_audit_log(
            action="read_file",
            user=principal.username,
            role=principal.role,
            ip=principal.ip,
            target=safe_path,
            ok=False,
            request_id=principal.request_id,
            extra={"error": "not_found"},
        )
        raise HTTPException(status_code=404, detail=f"文件不存在：{safe_path}") from exc

    write_audit_log(
        action="read_file",
        user=principal.username,
        role=principal.role,
        ip=principal.ip,
        target=safe_path,
        ok=True,
        request_id=principal.request_id,
        extra={"version": snapshot.version},
    )
    return snapshot


def save_file(
    repo: OSSRepository,
    *,
    path: str,
    content: str,
    base_version: str | None,
    force: bool,
    operation_id: str,
    user: dict[str, str],
    request: Request,
) -> SaveResult:
    principal = _principal_from_request(request, user)
    safe_path = repo.normalize_markdown_path(path)
    _enforce_markdown_size(content)

    try:
        result = repo.save_file(
            safe_path,
            content,
            base_version=base_version,
            force=force,
        )
    except VersionConflictError as exc:
        write_audit_log(
            action="save_file",
            user=principal.username,
            role=principal.role,
            ip=principal.ip,
            target=safe_path,
            ok=False,
            request_id=principal.request_id,
            operation_id=operation_id,
            extra={"error": "version_conflict", "client_version": base_version, "current_version": exc.current_version},
        )
        conflict_payload: dict[str, Any] = {
            "detail": "version_conflict",
            "path": safe_path,
            "current_version": exc.current_version,
            "current_content": exc.current_content,
        }
        raise HTTPException(status_code=409, detail=conflict_payload) from exc

    write_audit_log(
        action="save_file",
        user=principal.username,
        role=principal.role,
        ip=principal.ip,
        target=safe_path,
        ok=True,
        request_id=principal.request_id,
        operation_id=operation_id,
        extra={
            "version": result.version,
            "created": result.created,
            "force": force,
        },
    )
    return result


def delete_file(
    repo: OSSRepository,
    *,
    path: str,
    operation_id: str,
    user: dict[str, str],
    request: Request,
) -> str:
    principal = _principal_from_request(request, user)
    safe_path = repo.normalize_markdown_path(path)
    repo.delete_file(safe_path)
    write_audit_log(
        action="delete_file",
        user=principal.username,
        role=principal.role,
        ip=principal.ip,
        target=safe_path,
        ok=True,
        request_id=principal.request_id,
        operation_id=operation_id,
    )
    return safe_path


def upload_image(
    repo: OSSRepository,
    *,
    file: UploadFile,
    operation_id: str,
    user: dict[str, str],
    request: Request,
) -> str:
    principal = _principal_from_request(request, user)
    settings = get_settings()

    key = f"upload:{principal.ip}"
    allowed = _upload_rate_limiter.allow(
        key,
        limit=settings.upload_max_requests_per_minute,
        window_seconds=60,
    )
    if not allowed:
        write_audit_log(
            action="upload_image",
            user=principal.username,
            role=principal.role,
            ip=principal.ip,
            target=file.filename or "upload",
            ok=False,
            request_id=principal.request_id,
            operation_id=operation_id,
            extra={"error": "rate_limited"},
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="上传过于频繁，请稍后重试",
        )

    url = repo.upload_image(file)
    write_audit_log(
        action="upload_image",
        user=principal.username,
        role=principal.role,
        ip=principal.ip,
        target=file.filename or "upload",
        ok=True,
        request_id=principal.request_id,
        operation_id=operation_id,
        extra={"url": url},
    )
    return url
