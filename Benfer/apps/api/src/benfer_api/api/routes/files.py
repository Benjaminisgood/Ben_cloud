from datetime import datetime, timedelta
import secrets
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from benfer_api.core.config import get_settings
from benfer_api.db.database import get_db
from benfer_api.models.file import ClipboardItem, FileUpload
from benfer_api.schemas.file import (
    ClipboardItemCreate,
    ClipboardItemResponse,
    FileUploadCompleteRequest,
    FileUploadInitRequest,
    FileUploadInitResponse,
    FileUploadResponse,
    HealthResponse,
)
from benfer_api.services.clipboard import get_clipboard_service
from benfer_api.services.oss import get_oss_service
from benfer_api.utils.auth import get_current_user, get_optional_current_user

settings = get_settings()
router = APIRouter()


def _normalize_content_type(content_type: Optional[str]) -> str:
    if not content_type:
        return ""
    return content_type.split(";", 1)[0].strip().lower()


def _is_allowed_content_type(content_type: Optional[str]) -> bool:
    normalized = _normalize_content_type(content_type)
    if not normalized:
        return True

    for allowed in settings.allowed_file_content_types:
        if allowed.endswith("/*"):
            prefix = allowed[:-1]
            if normalized.startswith(prefix):
                return True
        elif normalized == allowed:
            return True
    return False


def _ensure_owner(resource_user_id: Optional[str], current_user: dict) -> None:
    user_id = current_user.get("user_id")
    if resource_user_id and resource_user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )


def _build_proxy_upload_url(upload_id: int, upload_token: str) -> str:
    return f"/api/files/{upload_id}/content?upload_token={upload_token}"


def _build_private_download_url(access_token: str) -> str:
    return f"/api/files/{access_token}/download/redirect"


def _build_public_download_url(access_token: str) -> str:
    return f"/api/files/public/{access_token}/download"


def _ensure_upload_access(
    db_file: FileUpload,
    current_user: Optional[dict],
    upload_token: Optional[str],
) -> None:
    if current_user:
        _ensure_owner(db_file.user_id, current_user)
        return

    if upload_token and db_file.access_token and secrets.compare_digest(upload_token, db_file.access_token):
        return

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")


def _get_file_by_access_token(db: Session, access_token: str) -> FileUpload:
    db_file = db.query(FileUpload).filter(FileUpload.access_token == access_token).first()
    if not db_file:
        raise HTTPException(status_code=404, detail="File not found")
    return db_file


def _ensure_downloadable(db_file: FileUpload) -> None:
    if db_file.upload_status != "completed":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="File upload is not completed yet")

    if db_file.expires_at and datetime.utcnow() > db_file.expires_at:
        raise HTTPException(status_code=410, detail="File expired")


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(status="ok")


@router.get("/clipboard", response_model=list[ClipboardItemResponse])
async def list_clipboard_items(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List current user's clipboard items."""
    user_id = current_user.get("user_id")
    items = (
        db.query(ClipboardItem)
        .filter(ClipboardItem.user_id == user_id)
        .order_by(ClipboardItem.created_at.desc())
        .limit(limit)
        .all()
    )
    return items


@router.post("/clipboard", response_model=ClipboardItemResponse)
async def create_clipboard_item(
    item: ClipboardItemCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Create a new clipboard item."""
    if len(item.content) > settings.MAX_CLIPBOARD_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Clipboard content too large; max {settings.MAX_CLIPBOARD_CHARS} characters",
        )

    clipboard_service = get_clipboard_service()

    access_token, expires_at = clipboard_service.save_clipboard(
        content=item.content,
        content_type=item.content_type,
        expires_in_hours=item.expires_in_hours,
    )

    db_item = ClipboardItem(
        content=item.content,
        content_type=item.content_type,
        user_id=current_user.get("user_id"),
        expires_at=expires_at,
        is_public=item.is_public,
        access_token=access_token,
    )

    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    return db_item


@router.get("/clipboard/{access_token}", response_model=ClipboardItemResponse)
async def get_clipboard_item(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Get clipboard item by access token."""
    item = (
        db.query(ClipboardItem)
        .filter(ClipboardItem.access_token == access_token)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Clipboard item not found")

    if item.expires_at and datetime.utcnow() > item.expires_at:
        raise HTTPException(status_code=410, detail="Clipboard item expired")

    if item.is_public:
        return item

    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    _ensure_owner(item.user_id, current_user)
    return item


@router.delete("/clipboard/{access_token}")
async def delete_clipboard_item(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete clipboard item."""
    item = (
        db.query(ClipboardItem)
        .filter(ClipboardItem.access_token == access_token)
        .first()
    )

    if not item:
        raise HTTPException(status_code=404, detail="Clipboard item not found")

    _ensure_owner(item.user_id, current_user)

    clipboard_service = get_clipboard_service()
    clipboard_service.delete_clipboard(access_token)

    db.delete(item)
    db.commit()

    return {"message": "Clipboard item deleted"}


@router.get("/files", response_model=list[FileUploadResponse])
async def list_files(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List current user's uploaded files."""
    user_id = current_user.get("user_id")
    files = (
        db.query(FileUpload)
        .filter(FileUpload.user_id == user_id)
        .order_by(FileUpload.created_at.desc())
        .limit(limit)
        .all()
    )
    return files


@router.post("/files/init", response_model=FileUploadInitResponse)
async def init_file_upload(
    request: FileUploadInitRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Initialize file upload and get presigned URLs."""
    if request.file_size <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="file_size must be greater than 0",
        )

    if request.file_size > settings.MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"file too large; max {settings.MAX_FILE_SIZE_BYTES} bytes",
        )

    if not _is_allowed_content_type(request.content_type):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"unsupported content_type: {request.content_type}",
        )

    if request.chunk_count < 1 or request.chunk_count > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="chunk_count out of allowed range (1-10000)",
        )

    oss_service = get_oss_service()
    user_id = current_user.get("user_id")
    oss_key = oss_service.generate_oss_key(request.filename, user_id)

    if request.expires_in_hours:
        expires_at = datetime.utcnow() + timedelta(hours=request.expires_in_hours)
    else:
        expires_at = datetime.utcnow() + timedelta(hours=settings.FILE_EXPIRATION_HOURS)

    db_file = FileUpload(
        filename=request.filename,
        oss_key=oss_key,
        file_size=request.file_size,
        content_type=request.content_type,
        user_id=user_id,
        expires_at=expires_at,
        is_public=request.is_public,
        access_token=secrets.token_urlsafe(32),
        upload_status="uploading",
        chunk_count=request.chunk_count,
        total_chunks=request.chunk_count,
    )

    db.add(db_file)
    db.commit()
    db.refresh(db_file)

    chunk_urls: list[str] = []
    multipart_upload_id: Optional[str] = None
    if request.chunk_count > 1:
        multipart_upload_id = oss_service.init_multipart_upload(
            oss_key,
            content_type=request.content_type,
        )
        for i in range(request.chunk_count):
            chunk_urls.append(
                oss_service.get_multipart_upload_url(
                    oss_key=oss_key,
                    multipart_upload_id=multipart_upload_id,
                    part_number=i + 1,
                )
            )
    else:
        chunk_urls.append(_build_proxy_upload_url(db_file.id, db_file.access_token))

    return FileUploadInitResponse(
        upload_id=db_file.id,
        access_token=db_file.access_token,
        oss_key=oss_key,
        chunk_upload_urls=chunk_urls,
        multipart_upload_id=multipart_upload_id,
        complete_upload_url=f"/api/files/{db_file.id}/complete",
    )


@router.post("/files/{upload_id}/complete", response_model=FileUploadResponse)
async def complete_file_upload(
    upload_id: int,
    complete_request: Optional[FileUploadCompleteRequest] = Body(default=None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Complete multipart upload."""
    db_file = db.query(FileUpload).filter(FileUpload.id == upload_id).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="Upload not found")

    _ensure_owner(db_file.user_id, current_user)

    oss_service = get_oss_service()
    if db_file.chunk_count > 1:
        if (
            not complete_request
            or not complete_request.multipart_upload_id
            or not complete_request.parts
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="multipart_upload_id and parts are required for multipart completion",
            )

        if len(complete_request.parts) != db_file.chunk_count:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="parts count does not match chunk_count",
            )

        try:
            oss_service.complete_multipart_upload(
                oss_key=db_file.oss_key,
                multipart_upload_id=complete_request.multipart_upload_id,
                parts=complete_request.parts,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="multipart complete failed",
            ) from exc
    else:
        if not oss_service.file_exists(db_file.oss_key):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="uploaded object not found on OSS",
            )

    db_file.upload_status = "completed"
    db.commit()
    db.refresh(db_file)
    return db_file


@router.api_route("/files/{upload_id}/content", methods=["POST", "PUT"], response_model=FileUploadResponse)
async def upload_file_content(
    upload_id: int,
    request: Request,
    upload_token: Optional[str] = Query(default=None),
    file: Optional[UploadFile] = File(default=None),
    db: Session = Depends(get_db),
    current_user: Optional[dict] = Depends(get_optional_current_user),
):
    """Upload path that proxies file bytes through Benfer for both new and legacy frontends."""
    db_file = db.query(FileUpload).filter(FileUpload.id == upload_id).first()

    if not db_file:
        raise HTTPException(status_code=404, detail="Upload not found")

    _ensure_upload_access(db_file, current_user, upload_token)

    if db_file.upload_status == "completed":
        return db_file

    upload_body: bytes | object
    content_type: Optional[str]

    if request.method == "POST":
        if file is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="missing file field",
            )

        file.file.seek(0, 2)
        actual_size = file.file.tell()
        file.file.seek(0)
        if actual_size != db_file.file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="uploaded file size mismatch",
            )

        content_type = file.content_type or db_file.content_type
        if not _is_allowed_content_type(content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unsupported content_type: {content_type}",
            )
        upload_body = file.file
    else:
        raw = await request.body()
        if len(raw) != db_file.file_size:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="uploaded file size mismatch",
            )

        content_type = request.headers.get("content-type") or db_file.content_type
        if not _is_allowed_content_type(content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"unsupported content_type: {content_type}",
            )
        upload_body = raw

    oss_service = get_oss_service()
    ok = oss_service.upload_file(
        db_file.oss_key,
        upload_body,
        content_type=content_type,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="proxy upload to OSS failed",
        )

    db_file.upload_status = "completed"
    db.commit()
    db.refresh(db_file)
    if file is not None:
        await file.close()
    return db_file


@router.get("/files/{access_token}", response_model=FileUploadResponse)
async def get_file_info(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get file upload info."""
    db_file = _get_file_by_access_token(db, access_token)
    _ensure_owner(db_file.user_id, current_user)
    return db_file


@router.get("/files/{access_token}/download")
async def download_file(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Download file with presigned URL."""
    db_file = _get_file_by_access_token(db, access_token)
    _ensure_owner(db_file.user_id, current_user)
    _ensure_downloadable(db_file)

    oss_service = get_oss_service()
    download_url = oss_service.get_download_url(db_file.oss_key)

    db_file.download_count += 1
    db.commit()

    return {
        "download_url": download_url,
        "filename": db_file.filename,
        "stable_download_url": _build_private_download_url(access_token),
        "public_download_url": _build_public_download_url(access_token) if db_file.is_public else None,
        "is_public": db_file.is_public,
    }


@router.get("/files/{access_token}/download/redirect")
async def redirect_private_file_download(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Stable owner-only download entry that redirects to a fresh OSS signed URL."""
    db_file = _get_file_by_access_token(db, access_token)
    _ensure_owner(db_file.user_id, current_user)
    _ensure_downloadable(db_file)

    oss_service = get_oss_service()
    download_url = oss_service.get_download_url(db_file.oss_key)

    db_file.download_count += 1
    db.commit()

    return RedirectResponse(download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/files/public/{access_token}/download")
async def redirect_public_file_download(
    access_token: str,
    db: Session = Depends(get_db),
):
    """Public share entry for files explicitly marked as public."""
    db_file = _get_file_by_access_token(db, access_token)
    if not db_file.is_public:
        raise HTTPException(status_code=404, detail="Public file not found")

    _ensure_downloadable(db_file)

    oss_service = get_oss_service()
    download_url = oss_service.get_download_url(db_file.oss_key)

    db_file.download_count += 1
    db.commit()

    return RedirectResponse(download_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.delete("/files/{access_token}")
async def delete_file(
    access_token: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Delete file."""
    db_file = _get_file_by_access_token(db, access_token)
    _ensure_owner(db_file.user_id, current_user)

    oss_service = get_oss_service()
    oss_service.delete_file(db_file.oss_key)

    db.delete(db_file)
    db.commit()

    return {"message": "File deleted"}
