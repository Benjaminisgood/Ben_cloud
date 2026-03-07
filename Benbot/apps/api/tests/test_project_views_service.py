from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from benbot_api.core.config import ProjectConfig
from benbot_api.schemas.web import SessionUserDTO
from benbot_api.services import project_views


class _Settings:
    def __init__(self, projects: list[ProjectConfig]) -> None:
        self._projects = projects

    def get_projects(self) -> list[ProjectConfig]:
        return self._projects


def _project(project_id: str = "benoss") -> ProjectConfig:
    return ProjectConfig(
        id=project_id,
        name="Benoss",
        description="desc",
        icon="book",
        port=8000,
        internal_url="http://localhost:8000",
        public_url="https://apps.example.com/benoss",
        sso_entry_path="/auth/sso",
        sso_enabled=True,
    )


def test_ensure_known_project_id_normalizes_and_validates(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_views, "get_settings", lambda: _Settings([_project("benoss")]))
    assert project_views.ensure_known_project_id("  BENOSS ") == "benoss"
    with pytest.raises(ValueError):
        project_views.ensure_known_project_id("unknown-app")


def test_assemble_projects_status_response_for_non_admin_hides_runtime_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_views, "get_settings", lambda: _Settings([_project("benlab")]))
    monkeypatch.setattr(
        project_views,
        "filter_visible_projects_for_user",
        lambda **kwargs: kwargs["projects"],
    )
    monkeypatch.setattr(project_views, "get_all_health", lambda _db: {})
    monkeypatch.setattr(project_views, "get_all_total_clicks", lambda _db: {"benlab": 9})
    monkeypatch.setattr(project_views, "get_project_runtime_states", lambda _ids: {"benlab": "running"})

    dto = project_views.assemble_projects_status_response(
        db=object(),
        current_user=SessionUserDTO(id=2, username="user", role="user", is_active=True),
    )
    assert dto.projects[0].id == "benlab"
    assert dto.projects[0].total_clicks == 9
    assert dto.projects[0].service_state is None


def test_assemble_project_logs_response_formats_output(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_views, "get_settings", lambda: _Settings([_project("benoss")]))
    fake_logs = [
        SimpleNamespace(
            id=1,
            level="INFO",
            source="system",
            message="ok",
            created_at=datetime(2026, 3, 6, 12, 30, 45),
        )
    ]
    monkeypatch.setattr(project_views, "get_logs", lambda *_args, **_kwargs: fake_logs)
    monkeypatch.setattr(project_views, "count_logs", lambda *_args, **_kwargs: 1)

    dto = project_views.assemble_project_logs_response(
        db=object(),
        project_id="BENOSS",
        level=None,
        limit=20,
        offset=0,
    )
    assert dto.project_id == "benoss"
    assert dto.total == 1
    assert dto.logs[0].created_at == "2026-03-06 12:30:45"


def test_assemble_projects_status_response_returns_empty_when_no_visible_projects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(project_views, "get_settings", lambda: _Settings([_project("benlab")]))
    monkeypatch.setattr(project_views, "filter_visible_projects_for_user", lambda **_kwargs: [])
    monkeypatch.setattr(project_views, "get_all_health", lambda _db: {})
    monkeypatch.setattr(project_views, "get_all_total_clicks", lambda _db: {"benlab": 9})
    monkeypatch.setattr(project_views, "get_project_runtime_states", lambda _ids: {"benlab": "running"})

    dto = project_views.assemble_projects_status_response(
        db=object(),
        current_user=SessionUserDTO(id=7, username="alice", role="user", is_active=True),
    )
    assert dto.projects == []
