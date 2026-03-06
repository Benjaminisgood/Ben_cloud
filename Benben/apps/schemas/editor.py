from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SaveFileRequest(BaseModel):
    path: str
    content: str
    base_version: str | None = None
    force: bool = False


class SaveFileResponse(BaseModel):
    status: str = "success"
    path: str
    version: str
    created: bool
    operation_id: str


class FileContentResponse(BaseModel):
    path: str
    content: str
    version: str


class FileListResponse(BaseModel):
    files: list[str]


class DeleteFileResponse(BaseModel):
    status: str = "success"
    path: str
    operation_id: str


class UploadImageResponse(BaseModel):
    url: str
    operation_id: str


class VersionConflictDetail(BaseModel):
    detail: str = "version_conflict"
    path: str
    current_version: str
    current_content: str


class TemplateMeta(BaseModel):
    id: str
    name: str
    description: str
    category: str
    variables: list[str]


class TemplateListResponse(BaseModel):
    templates: list[TemplateMeta]


class CreateFromTemplateRequest(BaseModel):
    path: str
    template_id: str
    project: str | None = None
    member: str | None = None
    force: bool = False


class CreateFromTemplateResponse(BaseModel):
    status: str = "success"
    path: str
    version: str
    created: bool
    template_id: str
    operation_id: str
    variables: dict[str, Any] = Field(default_factory=dict)


class ExportNoteRequest(BaseModel):
    format: Literal["txt", "md", "html"]
    content: str
    file_name: str | None = None
