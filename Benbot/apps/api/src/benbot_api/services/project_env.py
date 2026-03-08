from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from ..core.config import ProjectConfig, get_settings
from .logs import add_log

_MAX_ENV_FILE_BYTES = 256 * 1024


@dataclass
class ProjectEnvSnapshot:
    project_id: str
    project_name: str
    path: str
    loaded_from: str
    content: str
    exists: bool
    source: str
    updated_at: datetime | None


@dataclass
class ProjectEnvUpdateResult:
    project_id: str
    project_name: str
    path: str
    loaded_from: str
    exists: bool
    source: str
    updated_at: datetime
    change_id: str
    backup_path: str | None


def _workspace_root() -> Path:
    return get_settings().REPO_ROOT.parent


def _project_map() -> dict[str, ProjectConfig]:
    return {project.id: project for project in get_settings().get_projects()}


def _resolve_project(project_id: str) -> ProjectConfig:
    normalized = project_id.strip().lower()
    project = _project_map().get(normalized)
    if project is None:
        raise ValueError("project_not_found")
    return project


def _resolve_project_root(project: ProjectConfig) -> Path:
    workspace_root = _workspace_root().resolve()
    project_root = _workspace_root() / project.name
    if not project_root.exists() or not project_root.is_dir():
        raise ValueError("project_root_not_found")

    resolved_root = project_root.resolve()
    try:
        resolved_root.relative_to(workspace_root)
    except ValueError as exc:
        raise ValueError("project_root_out_of_workspace") from exc
    return project_root


def _relative_to_workspace(path: Path) -> str:
    return str(path.relative_to(_workspace_root()))


def _ensure_safe_file(path: Path, *, error_prefix: str = "env") -> None:
    if path.is_symlink():
        raise ValueError(f"{error_prefix}_symlink_not_allowed")
    if path.exists() and path.is_dir():
        raise ValueError(f"{error_prefix}_path_is_directory")


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("env_file_not_utf8") from exc


def _timestamp_for(path: Path) -> datetime:
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)


def read_project_env_file(project_id: str) -> ProjectEnvSnapshot:
    project = _resolve_project(project_id)
    project_root = _resolve_project_root(project)
    env_path = project_root / ".env"
    example_path = project_root / ".env.example"

    if env_path.exists():
        _ensure_safe_file(env_path, error_prefix="env")
        return ProjectEnvSnapshot(
            project_id=project.id,
            project_name=project.name,
            path=_relative_to_workspace(env_path),
            loaded_from=_relative_to_workspace(env_path),
            content=_read_text_file(env_path),
            exists=True,
            source="env",
            updated_at=_timestamp_for(env_path),
        )

    if example_path.exists():
        _ensure_safe_file(example_path, error_prefix="env_example")
        return ProjectEnvSnapshot(
            project_id=project.id,
            project_name=project.name,
            path=_relative_to_workspace(env_path),
            loaded_from=_relative_to_workspace(example_path),
            content=_read_text_file(example_path),
            exists=False,
            source="example",
            updated_at=_timestamp_for(example_path),
        )

    return ProjectEnvSnapshot(
        project_id=project.id,
        project_name=project.name,
        path=_relative_to_workspace(env_path),
        loaded_from="",
        content="",
        exists=False,
        source="empty",
        updated_at=None,
    )


def _create_backup(env_path: Path, project_id: str, change_id: str) -> str:
    backup_root = get_settings().REPO_ROOT / "backups" / "env-files" / project_id
    backup_root.mkdir(parents=True, exist_ok=True)
    backup_path = backup_root / f"{change_id}.env"
    shutil.copy2(env_path, backup_path)
    return str(backup_path.relative_to(_workspace_root()))


def update_project_env_file(
    *,
    project_id: str,
    content: str,
    db: Session,
    operator: str,
) -> ProjectEnvUpdateResult:
    project = _resolve_project(project_id)
    project_root = _resolve_project_root(project)
    env_path = project_root / ".env"

    if "\x00" in content:
        raise ValueError("env_contains_nul")
    if len(content.encode("utf-8")) > _MAX_ENV_FILE_BYTES:
        raise ValueError("env_too_large")

    if env_path.exists():
        _ensure_safe_file(env_path, error_prefix="env")

    change_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    backup_path = _create_backup(env_path, project.id, change_id) if env_path.exists() else None
    tmp_path = project_root / f".env.tmp.{change_id}"

    try:
        tmp_path.write_text(content, encoding="utf-8")
        if env_path.exists():
            try:
                shutil.copymode(env_path, tmp_path)
            except OSError:
                pass
        tmp_path.replace(env_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    updated_at = _timestamp_for(env_path)
    path = _relative_to_workspace(env_path)
    add_log(
        db,
        project.id,
        (
            f"[{operator}] 更新 .env | change_id: {change_id} | "
            f"path: {path} | backup: {backup_path or 'none'}"
        ),
        level="INFO",
        source="env_editor",
    )

    return ProjectEnvUpdateResult(
        project_id=project.id,
        project_name=project.name,
        path=path,
        loaded_from=path,
        exists=True,
        source="env",
        updated_at=updated_at,
        change_id=change_id,
        backup_path=backup_path,
    )
