from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ProjectItemStatus(BaseModel):
    id: str
    name: str
    status: str
    response_ms: Optional[int] = None
    total_clicks: int
    service_state: Optional[str] = None


class ProjectsStatusResponse(BaseModel):
    projects: list[ProjectItemStatus]


class ProjectControlResponse(BaseModel):
    ok: bool
    project_id: str
    action: str
    service_state: str
    output: str


class ProjectLogItem(BaseModel):
    id: int
    level: str
    source: str
    message: str
    created_at: str


class ProjectLogsResponse(BaseModel):
    project_id: str
    total: int
    offset: int
    limit: int
    logs: list[ProjectLogItem]


class ProjectEnvFileResponse(BaseModel):
    project_id: str
    project_name: str
    path: str
    loaded_from: str
    exists: bool
    source: str
    updated_at: Optional[str] = None
    content: str


class ProjectEnvUpdatePayload(BaseModel):
    content: str = Field(default="", max_length=262144)


class ProjectEnvUpdateResponse(BaseModel):
    ok: bool
    project_id: str
    project_name: str
    path: str
    loaded_from: str
    exists: bool
    source: str
    updated_at: str
    change_id: str
    backup_path: Optional[str] = None
