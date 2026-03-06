from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import Request
from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..schemas.web import (
    DashboardPageContextDTO,
    FlashMessageDTO,
    LoginPageContextDTO,
    ProjectCardDTO,
    ProjectRedirectTargetDTO,
    RegisterPageContextDTO,
    SessionUserDTO,
)
from .health import get_all_health
from .project_control import get_project_runtime_states
from .sso import create_sso_token
from .stats import get_all_total_clicks, record_click


def sanitize_next_url(raw_next: str) -> str:
    candidate = (raw_next or "").strip()
    if not candidate:
        return "/"

    parsed = urlsplit(candidate)
    if parsed.scheme or parsed.netloc:
        return "/"
    if not parsed.path.startswith("/") or parsed.path.startswith("//"):
        return "/"
    return candidate


def assemble_flash_messages(raw_messages: list[list[str]] | None) -> list[FlashMessageDTO]:
    messages: list[FlashMessageDTO] = []
    for item in raw_messages or []:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            continue
        category = str(item[0] or "info")
        text = str(item[1] or "").strip()
        if not text:
            continue
        messages.append(FlashMessageDTO(category=category, text=text))
    return messages


def _resolve_project_entry_base_url(request: Request, public_url: str, port: int) -> str:
    raw = (public_url or "").strip()
    parsed = urlsplit(raw)
    if parsed.scheme and parsed.netloc:
        return urlunsplit((parsed.scheme, parsed.netloc, parsed.path.rstrip("/"), parsed.query, parsed.fragment))

    scheme = request.url.scheme or "http"
    hostname = request.url.hostname or "localhost"
    host_for_url = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    return f"{scheme}://{host_for_url}:{port}"


def _build_project_redirect_url(
    request: Request,
    *,
    public_url: str,
    port: int,
    sso_entry_path: str,
    token: str | None,
) -> str:
    base_url = _resolve_project_entry_base_url(request, public_url, port)
    base = urlsplit(base_url)
    base_path = base.path.rstrip("/")
    entry_path = sso_entry_path if sso_entry_path.startswith("/") else f"/{sso_entry_path}"
    target_path = f"{base_path}{entry_path}" if base_path else entry_path

    query_pairs = parse_qsl(base.query, keep_blank_values=True)
    if token:
        query_pairs.append(("token", token))
    query = urlencode(query_pairs)
    return urlunsplit((base.scheme, base.netloc, target_path, query, ""))


def assemble_dashboard_page_context(
    *,
    db: Session,
    current_user: SessionUserDTO,
    flash_messages: list[list[str]] | None = None,
) -> DashboardPageContextDTO:
    settings = get_settings()
    projects = settings.get_projects()
    health_map = get_all_health(db)
    clicks_map = get_all_total_clicks(db)
    runtime_states = (
        get_project_runtime_states(project.id for project in projects)
        if current_user.role == "admin"
        else {}
    )

    project_cards = [
        ProjectCardDTO(
            id=proj.id,
            name=proj.name,
            description=proj.description,
            icon=proj.icon,
            color=proj.color,
            status=health_map[proj.id].status if proj.id in health_map else "unknown",
            response_ms=health_map[proj.id].response_ms if proj.id in health_map else None,
            last_checked=health_map[proj.id].last_checked if proj.id in health_map else None,
            total_clicks=clicks_map.get(proj.id, 0),
            public_url=proj.public_url,
            service_state=runtime_states.get(proj.id, "unknown"),
        )
        for proj in projects
    ]

    return DashboardPageContextDTO(
        current_user=current_user,
        projects=project_cards,
        flash_messages=assemble_flash_messages(flash_messages),
    )


def assemble_login_page_context(
    *,
    flash_messages: list[list[str]] | None = None,
    next_url: str = "/",
) -> LoginPageContextDTO:
    return LoginPageContextDTO(
        next_url=sanitize_next_url(next_url),
        flash_messages=assemble_flash_messages(flash_messages),
    )


def assemble_register_page_context(
    *,
    flash_messages: list[list[str]] | None = None,
) -> RegisterPageContextDTO:
    return RegisterPageContextDTO(
        flash_messages=assemble_flash_messages(flash_messages),
    )


def assemble_project_redirect_target(
    *,
    project_id: str,
    request: Request,
    db: Session,
    current_user: SessionUserDTO,
) -> ProjectRedirectTargetDTO | None:
    settings = get_settings()
    projects = {project.id: project for project in settings.get_projects()}
    project = projects.get(project_id)
    if project is None:
        return None

    record_click(db, project_id)
    token = (
        create_sso_token(settings.SSO_SECRET, current_user.username, current_user.role)
        if project.sso_enabled
        else None
    )
    redirect_url = _build_project_redirect_url(
        request,
        public_url=project.public_url,
        port=project.port,
        sso_entry_path=project.sso_entry_path,
        token=token,
    )
    return ProjectRedirectTargetDTO(project_id=project.id, redirect_url=redirect_url)
