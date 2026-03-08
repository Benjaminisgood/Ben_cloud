from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from benbot_api.api.routes import projects as projects_route
from benbot_api.services.project_env import ProjectEnvSnapshot, ProjectEnvUpdateResult


def test_get_project_env_file_returns_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        projects_route,
        "read_project_env_file",
        lambda _project_id: ProjectEnvSnapshot(
            project_id="benoss",
            project_name="Benoss",
            path="Benoss/.env",
            loaded_from="Benoss/.env.example",
            content="DEBUG=true\n",
            exists=False,
            source="example",
            updated_at=None,
        ),
    )

    response = projects_route.get_project_env_file("benoss", request=object(), db=object())

    assert response.project_id == "benoss"
    assert response.project_name == "Benoss"
    assert response.path == "Benoss/.env"
    assert response.loaded_from == "Benoss/.env.example"
    assert response.source == "example"
    assert response.content == "DEBUG=true\n"


def test_put_project_env_file_returns_change_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        projects_route,
        "update_project_env_file",
        lambda **_kwargs: ProjectEnvUpdateResult(
            project_id="benoss",
            project_name="Benoss",
            path="Benoss/.env",
            loaded_from="Benoss/.env",
            exists=True,
            source="env",
            updated_at=datetime(2026, 3, 8, 10, 0, 0),
            change_id="20260308100000000000",
            backup_path="Benbot/backups/env-files/benoss/20260308100000000000.env",
        ),
    )

    response = projects_route.put_project_env_file(
        "benoss",
        payload=projects_route.ProjectEnvUpdatePayload(content="APP_ENV=prod\n"),
        request=object(),
        db=object(),
    )

    assert response.ok is True
    assert response.project_id == "benoss"
    assert response.change_id == "20260308100000000000"
    assert response.backup_path == "Benbot/backups/env-files/benoss/20260308100000000000.env"


def test_get_project_env_file_maps_project_not_found_to_404(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        projects_route,
        "read_project_env_file",
        lambda _project_id: (_ for _ in ()).throw(ValueError("project_not_found")),
    )

    with pytest.raises(HTTPException) as exc_info:
        projects_route.get_project_env_file("missing", request=object(), db=object())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "project_not_found"
