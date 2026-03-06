from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile

from ...core.auth import require_session_user
from ...schemas.editor import (
    CreateFromTemplateRequest,
    CreateFromTemplateResponse,
    DeleteFileResponse,
    ExportNoteRequest,
    FileContentResponse,
    FileListResponse,
    SaveFileRequest,
    SaveFileResponse,
    TemplateListResponse,
    TemplateMeta,
    UploadImageResponse,
)
from ...services import editor as editor_service
from ...services.audit import new_operation_id, write_audit_log
from ...services.exporter import build_export_artifact
from ...services.storage import OSSRepository, get_repository
from ...services.templates import (
    build_template_variables,
    get_template,
    list_templates,
    render_template_content,
)

router = APIRouter(tags=["editor"])


@router.get("/api/session")
async def get_session(request: Request):
    user = require_session_user(request)
    return {"username": user["username"], "role": user["role"]}


@router.get("/api/files", response_model=FileListResponse)
async def list_files(request: Request, repo: OSSRepository = Depends(get_repository)):
    user = require_session_user(request)
    files = editor_service.list_files(repo, user=user, request=request)
    return FileListResponse(files=files)


@router.get("/api/files/{path:path}", response_model=FileContentResponse)
async def get_file(path: str, request: Request, repo: OSSRepository = Depends(get_repository)):
    user = require_session_user(request)
    snapshot = editor_service.read_file(repo, path=path, user=user, request=request)
    return FileContentResponse(path=snapshot.path, content=snapshot.content, version=snapshot.version)


@router.post("/api/files", response_model=SaveFileResponse)
async def save_file(payload: SaveFileRequest, request: Request, repo: OSSRepository = Depends(get_repository)):
    user = require_session_user(request)
    operation_id = new_operation_id()
    result = editor_service.save_file(
        repo,
        path=payload.path,
        content=payload.content,
        base_version=payload.base_version,
        force=payload.force,
        operation_id=operation_id,
        user=user,
        request=request,
    )
    return SaveFileResponse(path=result.path, version=result.version, created=result.created, operation_id=operation_id)


@router.delete("/api/files/{path:path}", response_model=DeleteFileResponse)
async def delete_file(path: str, request: Request, repo: OSSRepository = Depends(get_repository)):
    user = require_session_user(request)
    operation_id = new_operation_id()
    safe_path = editor_service.delete_file(
        repo,
        path=path,
        operation_id=operation_id,
        user=user,
        request=request,
    )
    return DeleteFileResponse(path=safe_path, operation_id=operation_id)


@router.post("/api/upload", response_model=UploadImageResponse)
async def upload_image(request: Request, file: UploadFile = File(...), repo: OSSRepository = Depends(get_repository)):
    user = require_session_user(request)
    operation_id = new_operation_id()
    url = editor_service.upload_image(
        repo,
        file=file,
        operation_id=operation_id,
        user=user,
        request=request,
    )
    return UploadImageResponse(url=url, operation_id=operation_id)


@router.get("/api/templates", response_model=TemplateListResponse)
async def get_templates(request: Request):
    require_session_user(request)
    templates = [
        TemplateMeta(
            id=item.id,
            name=item.name,
            description=item.description,
            category=item.category,
            variables=item.variables,
        )
        for item in list_templates()
    ]
    return TemplateListResponse(templates=templates)


@router.post("/api/export")
async def export_note(payload: ExportNoteRequest, request: Request):
    user = require_session_user(request)
    operation_id = new_operation_id()
    request_id = str(getattr(request.state, "request_id", "") or "").strip() or "unknown"

    try:
        artifact = build_export_artifact(
            export_format=payload.format,
            content=payload.content,
            file_name=payload.file_name,
        )
    except ValueError as exc:
        write_audit_log(
            action="export_note",
            user=user["username"],
            role=user["role"],
            ip=(request.client.host if request.client else "unknown"),
            target=payload.file_name or "note",
            ok=False,
            request_id=request_id,
            operation_id=operation_id,
            extra={"error": "unsupported_export_format", "format": payload.format},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    write_audit_log(
        action="export_note",
        user=user["username"],
        role=user["role"],
        ip=(request.client.host if request.client else "unknown"),
        target=artifact.filename,
        ok=True,
        request_id=request_id,
        operation_id=operation_id,
        extra={"format": payload.format, "size_bytes": len(artifact.content)},
    )

    headers = {
        "Content-Disposition": f'attachment; filename="{artifact.filename}"',
        "X-Operation-ID": operation_id,
    }
    return Response(content=artifact.content, media_type=artifact.media_type, headers=headers)


@router.post("/api/files/from-template", response_model=CreateFromTemplateResponse)
async def create_from_template(
    payload: CreateFromTemplateRequest,
    request: Request,
    repo: OSSRepository = Depends(get_repository),
):
    user = require_session_user(request)
    operation_id = new_operation_id()

    try:
        template = get_template(payload.template_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    safe_path = repo.normalize_markdown_path(payload.path)

    variables = build_template_variables(
        username=user["username"],
        project=payload.project,
        member=payload.member,
        file_path=safe_path,
    )
    content = render_template_content(template.id, variables=variables)

    result = editor_service.save_file(
        repo,
        path=safe_path,
        content=content,
        base_version=None,
        force=payload.force,
        operation_id=operation_id,
        user=user,
        request=request,
    )

    request_id = str(getattr(request.state, "request_id", "") or "").strip() or "unknown"
    write_audit_log(
        action="template_create",
        user=user["username"],
        role=user["role"],
        ip=(request.client.host if request.client else "unknown"),
        target=result.path,
        ok=True,
        request_id=request_id,
        operation_id=operation_id,
        extra={"template_id": template.id, "version": result.version, "created": result.created},
    )

    return CreateFromTemplateResponse(
        path=result.path,
        version=result.version,
        created=result.created,
        template_id=template.id,
        operation_id=operation_id,
        variables=variables,
    )
