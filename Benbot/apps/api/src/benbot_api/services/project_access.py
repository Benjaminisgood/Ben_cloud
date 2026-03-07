from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from sqlalchemy.orm import Session

from ..core.config import ProjectConfig, get_settings
from ..models.user import User
from ..repositories import (
    create_project_log,
    get_user_by_id,
    list_access_rows_for_users,
    list_project_ids_for_user,
    list_users,
    replace_user_project_access,
    trim_project_logs,
)
from ..schemas.web import SessionUserDTO

_PROJECT_ACCESS_LOG_PROJECT_ID = "benbot"
_MAX_PROJECT_LOG_ENTRIES = 500


@dataclass(frozen=True)
class UserProjectAccessOverview:
    projects: list[ProjectConfig]
    users: list[User]
    access_map: dict[int, list[str]]


def _normalize_project_ids(project_ids: Iterable[str]) -> list[str]:
    return sorted({project_id.strip().lower() for project_id in project_ids if project_id.strip()})


def _known_project_ids() -> set[str]:
    return {project.id for project in get_settings().get_projects()}


def filter_visible_projects_for_user(
    *,
    db: Session,
    current_user: SessionUserDTO,
    projects: list[ProjectConfig],
) -> list[ProjectConfig]:
    if current_user.role == "admin":
        return projects

    allowed_ids = set(list_project_ids_for_user(db, current_user.id))
    if not allowed_ids:
        return []
    return [project for project in projects if project.id in allowed_ids]


def can_user_access_project(
    *,
    db: Session,
    current_user: SessionUserDTO,
    project_id: str,
) -> bool:
    if current_user.role == "admin":
        return True

    allowed_ids = set(list_project_ids_for_user(db, current_user.id))
    return project_id in allowed_ids


def assemble_user_project_access_overview(*, db: Session) -> UserProjectAccessOverview:
    projects = get_settings().get_projects()
    users = list_users(db)
    non_admin_user_ids = [user.id for user in users if user.role != "admin"]
    access_rows = list_access_rows_for_users(db, non_admin_user_ids)

    access_map: dict[int, list[str]] = {user_id: [] for user_id in non_admin_user_ids}
    for row in access_rows:
        existing = access_map.setdefault(row.user_id, [])
        existing.append(row.project_id)
    for user_id, project_ids in access_map.items():
        access_map[user_id] = sorted(set(project_ids))

    return UserProjectAccessOverview(
        projects=projects,
        users=users,
        access_map=access_map,
    )


def _create_access_change_log(
    *,
    db: Session,
    operator: str,
    target_user: User,
    project_ids: list[str],
) -> int:
    message = (
        f"operator={operator} updated user={target_user.username}(id={target_user.id}) "
        f"project_access={','.join(project_ids) if project_ids else '<none>'}"
    )
    entry = create_project_log(
        db,
        project_id=_PROJECT_ACCESS_LOG_PROJECT_ID,
        level="INFO",
        source="access_control",
        message=message,
    )
    trim_project_logs(db, project_id=_PROJECT_ACCESS_LOG_PROJECT_ID, max_entries=_MAX_PROJECT_LOG_ENTRIES)
    return entry.id


def update_user_project_access(
    *,
    db: Session,
    operator: str,
    user_id: int,
    project_ids: Iterable[str],
) -> tuple[User, list[str], int]:
    target_user = get_user_by_id(db, user_id)
    if target_user is None:
        raise ValueError("user_not_found")
    if target_user.role == "admin":
        raise ValueError("admin_access_fixed")

    normalized_ids = _normalize_project_ids(project_ids)
    unknown_ids = sorted(set(normalized_ids) - _known_project_ids())
    if unknown_ids:
        raise ValueError("invalid_project_ids:" + ",".join(unknown_ids))

    replace_user_project_access(
        db,
        user_id=target_user.id,
        project_ids=normalized_ids,
        granted_by=operator,
    )
    change_id = _create_access_change_log(
        db=db,
        operator=operator,
        target_user=target_user,
        project_ids=normalized_ids,
    )
    return target_user, normalized_ids, change_id
