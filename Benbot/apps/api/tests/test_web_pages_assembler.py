from __future__ import annotations

import pytest

from benbot_api.core.config import ProjectConfig
from benbot_api.schemas.web import SessionUserDTO
from benbot_api.services import web_pages


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


def test_assemble_dashboard_context_for_admin_includes_runtime_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_pages, "get_settings", lambda: _Settings([_project()]))
    monkeypatch.setattr(web_pages, "get_all_health", lambda _db: {})
    monkeypatch.setattr(web_pages, "get_all_total_clicks", lambda _db: {"benoss": 3})
    monkeypatch.setattr(web_pages, "get_project_runtime_states", lambda _ids: {"benoss": "running"})

    dto = web_pages.assemble_dashboard_page_context(
        db=object(),
        current_user=SessionUserDTO(id=1, username="admin", role="admin", is_active=True),
        flash_messages=[["info", "ok"]],
    )

    assert dto.current_user.username == "admin"
    assert dto.projects[0].service_state == "running"
    assert dto.projects[0].total_clicks == 3
    assert len(dto.flash_messages) == 1
    assert dto.flash_messages[0].category == "info"
    assert dto.flash_messages[0].text == "ok"


def test_assemble_dashboard_context_for_non_admin_hides_runtime_states(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(web_pages, "get_settings", lambda: _Settings([_project("benlab")]))
    monkeypatch.setattr(web_pages, "get_all_health", lambda _db: {})
    monkeypatch.setattr(web_pages, "get_all_total_clicks", lambda _db: {})
    monkeypatch.setattr(web_pages, "get_project_runtime_states", lambda _ids: {"benlab": "running"})

    dto = web_pages.assemble_dashboard_page_context(
        db=object(),
        current_user=SessionUserDTO(id=2, username="user", role="user", is_active=True),
        flash_messages=[],
    )

    assert dto.projects[0].id == "benlab"
    assert dto.projects[0].service_state == "unknown"


def test_assemble_login_context_sanitizes_next_and_converts_flash() -> None:
    dto = web_pages.assemble_login_page_context(
        flash_messages=[["error", "bad credentials"]],
        next_url="https://evil.example/",
    )
    assert dto.next_url == "/"
    assert dto.flash_messages[0].category == "error"
    assert dto.flash_messages[0].text == "bad credentials"


def test_assemble_register_context_drops_invalid_flash_items() -> None:
    raw_messages = [["success", "ok"], ["only-one-item"]]
    dto = web_pages.assemble_register_page_context(
        flash_messages=raw_messages,
    )
    assert len(dto.flash_messages) == 1
    assert dto.flash_messages[0].category == "success"
