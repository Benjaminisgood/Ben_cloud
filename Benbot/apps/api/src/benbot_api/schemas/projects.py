from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


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
