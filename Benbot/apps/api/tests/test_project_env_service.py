from __future__ import annotations

from pathlib import Path

import pytest

from benbot_api.core.config import ProjectConfig
from benbot_api.services import project_env


class _Settings:
    def __init__(self, repo_root: Path, projects: list[ProjectConfig]) -> None:
        self.REPO_ROOT = repo_root
        self._projects = projects

    def get_projects(self) -> list[ProjectConfig]:
        return self._projects


def _project(project_id: str = "benoss", name: str = "Benoss") -> ProjectConfig:
    return ProjectConfig(
        id=project_id,
        name=name,
        description="desc",
        icon="icon",
        port=8000,
        internal_url="http://localhost:8000",
        public_url="https://apps.example.com/benoss",
    )


def _settings_for(tmp_path: Path, projects: list[ProjectConfig]) -> _Settings:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    repo_root = workspace_root / "Benbot"
    repo_root.mkdir()
    return _Settings(repo_root=repo_root, projects=projects)


def test_read_project_env_file_prefers_real_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings_for(tmp_path, [_project()])
    project_root = settings.REPO_ROOT.parent / "Benoss"
    project_root.mkdir()
    (project_root / ".env").write_text("APP_ENV=prod\n", encoding="utf-8")
    (project_root / ".env.example").write_text("APP_ENV=dev\n", encoding="utf-8")
    monkeypatch.setattr(project_env, "get_settings", lambda: settings)

    snapshot = project_env.read_project_env_file("benoss")

    assert snapshot.project_id == "benoss"
    assert snapshot.exists is True
    assert snapshot.source == "env"
    assert snapshot.path == "Benoss/.env"
    assert snapshot.loaded_from == "Benoss/.env"
    assert snapshot.content == "APP_ENV=prod\n"
    assert snapshot.updated_at is not None


def test_read_project_env_file_falls_back_to_example(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings_for(tmp_path, [_project()])
    project_root = settings.REPO_ROOT.parent / "Benoss"
    project_root.mkdir()
    (project_root / ".env.example").write_text("DEBUG=true\n", encoding="utf-8")
    monkeypatch.setattr(project_env, "get_settings", lambda: settings)

    snapshot = project_env.read_project_env_file("benoss")

    assert snapshot.exists is False
    assert snapshot.source == "example"
    assert snapshot.path == "Benoss/.env"
    assert snapshot.loaded_from == "Benoss/.env.example"
    assert snapshot.content == "DEBUG=true\n"


def test_update_project_env_file_writes_backup_and_log(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    settings = _settings_for(tmp_path, [_project()])
    project_root = settings.REPO_ROOT.parent / "Benoss"
    project_root.mkdir()
    env_path = project_root / ".env"
    env_path.write_text("OLD_SECRET=1\n", encoding="utf-8")
    monkeypatch.setattr(project_env, "get_settings", lambda: settings)

    captured_log: dict[str, str] = {}

    def _add_log(_db, project_id: str, message: str, level: str = "INFO", source: str = "system") -> None:
        captured_log["project_id"] = project_id
        captured_log["message"] = message
        captured_log["level"] = level
        captured_log["source"] = source

    monkeypatch.setattr(project_env, "add_log", _add_log)

    result = project_env.update_project_env_file(
        project_id="benoss",
        content="NEW_SECRET=2\n",
        db=object(),
        operator="root",
    )

    assert env_path.read_text(encoding="utf-8") == "NEW_SECRET=2\n"
    assert result.project_id == "benoss"
    assert result.source == "env"
    assert result.loaded_from == "Benoss/.env"
    assert result.change_id
    assert result.backup_path is not None
    assert (settings.REPO_ROOT.parent / result.backup_path).read_text(encoding="utf-8") == "OLD_SECRET=1\n"
    assert captured_log["project_id"] == "benoss"
    assert captured_log["level"] == "INFO"
    assert captured_log["source"] == "env_editor"
    assert result.change_id in captured_log["message"]
