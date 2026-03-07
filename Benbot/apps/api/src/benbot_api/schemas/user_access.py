from __future__ import annotations

from pydantic import BaseModel, Field


class AccessProjectOption(BaseModel):
    id: str
    name: str


class AccessUserItem(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool
    project_ids: list[str] = Field(default_factory=list)


class UserProjectAccessOverviewResponse(BaseModel):
    projects: list[AccessProjectOption]
    users: list[AccessUserItem]


class UserProjectAccessUpdatePayload(BaseModel):
    project_ids: list[str] = Field(default_factory=list)


class UserProjectAccessUpdateResponse(BaseModel):
    ok: bool
    user_id: int
    project_ids: list[str]
    change_id: int
