from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TemplateContextDTO(BaseModel):
    def to_template_context(self) -> dict[str, Any]:
        return self.model_dump(mode="python")


class FlashMessageDTO(BaseModel):
    category: str
    text: str


class SessionUserDTO(BaseModel):
    id: int
    username: str
    role: str
    is_active: bool = True


class ApiTokenUserDTO(BaseModel):
    id: int = -1
    username: str = "nanobot"
    role: str = "admin"
    is_active: bool = True
    scopes: set[str] = Field(default_factory=set)

    def has_scope(self, scope: str) -> bool:
        return scope in self.scopes


class ProjectCardDTO(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    color: str
    status: str
    response_ms: int | None = None
    last_checked: datetime | None = None
    total_clicks: int
    public_url: str
    service_state: str = "unknown"


class DashboardPageContextDTO(TemplateContextDTO):
    title: str = "Benbot · 控制台"
    page: str = "home"
    current_user: SessionUserDTO
    projects: list[ProjectCardDTO]
    flash_messages: list[FlashMessageDTO] = Field(default_factory=list)


class ManagementPageContextDTO(TemplateContextDTO):
    title: str = "Benbot · 管理页"
    page: str = "manage"
    current_user: SessionUserDTO
    projects: list[ProjectCardDTO]
    flash_messages: list[FlashMessageDTO] = Field(default_factory=list)


class LoginPageContextDTO(TemplateContextDTO):
    title: str = "登录 · Benbot"
    page: str = "login"
    flash_messages: list[FlashMessageDTO] = Field(default_factory=list)
    next_url: str = "/"


class RegisterPageContextDTO(TemplateContextDTO):
    title: str = "注册 · Benbot"
    page: str = "register"
    flash_messages: list[FlashMessageDTO] = Field(default_factory=list)


class ProjectRedirectTargetDTO(BaseModel):
    project_id: str
    redirect_url: str
