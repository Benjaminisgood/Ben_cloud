from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from ..core.config import get_settings
from ..schemas.projects import ProjectItemStatus, ProjectLogItem, ProjectLogsResponse, ProjectsStatusResponse
from ..schemas.web import SessionUserDTO
from .health import get_all_health
from .logs import count_logs, get_logs
from .project_control import get_project_runtime_states
from .stats import get_all_total_clicks


def normalize_project_id(project_id: str) -> str:
    return project_id.strip().lower()


def ensure_known_project_id(project_id: str) -> str:
    normalized = normalize_project_id(project_id)
    known_ids = {project.id for project in get_settings().get_projects()}
    if normalized not in known_ids:
        raise ValueError("project_not_found")
    return normalized


def assemble_projects_status_response(
    *,
    db: Session,
    current_user: SessionUserDTO,
) -> ProjectsStatusResponse:
    projects = get_settings().get_projects()
    health_map = get_all_health(db)
    clicks_map = get_all_total_clicks(db)
    runtime_states = get_project_runtime_states(p.id for p in projects) if current_user.role == "admin" else {}

    return ProjectsStatusResponse(
        projects=[
            ProjectItemStatus(
                id=project.id,
                name=project.name,
                status=health_map[project.id].status if project.id in health_map else "unknown",
                response_ms=health_map[project.id].response_ms if project.id in health_map else None,
                total_clicks=clicks_map.get(project.id, 0),
                service_state=runtime_states.get(project.id),
            )
            for project in projects
        ]
    )


def assemble_project_logs_response(
    *,
    db: Session,
    project_id: str,
    level: Optional[str],
    limit: int,
    offset: int,
) -> ProjectLogsResponse:
    normalized = ensure_known_project_id(project_id)
    logs = get_logs(db, normalized, level=level, limit=limit, offset=offset)
    total = count_logs(db, normalized, level=level)

    return ProjectLogsResponse(
        project_id=normalized,
        total=total,
        offset=offset,
        limit=limit,
        logs=[
            ProjectLogItem(
                id=entry.id,
                level=entry.level,
                source=entry.source,
                message=entry.message,
                created_at=entry.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            )
            for entry in logs
        ],
    )
