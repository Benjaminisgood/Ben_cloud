from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest
from fastapi import HTTPException

from benbot_api.api.routes import projects as projects_route
from benbot_api.services.project_control import ProjectControlResult


@dataclass
class _User:
    role: str
    username: str = "admin"


async def _noop_async() -> None:
    return None


def _forbidden_admin_user(_request, _db):
    raise HTTPException(status_code=403, detail="forbidden")


def test_control_project_admin_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: _User(role="admin"),
    )
    monkeypatch.setattr(projects_route, "run_health_checks", _noop_async)

    def _run_project_control_action(_project_id, _action, **kwargs):
        assert kwargs.get("operator") == "admin"
        return ProjectControlResult(
            project_id="benoss",
            action="start",
            ok=True,
            service_state="running",
            output="ok",
            exit_code=0,
        )

    monkeypatch.setattr(
        projects_route,
        "run_project_control_action",
        _run_project_control_action,
    )

    payload = projects_route.ProjectControlPayload(action="start")
    result = asyncio.run(projects_route.control_project("benoss", payload, request=object(), db=object()))

    assert result["ok"] is True
    assert result["project_id"] == "benoss"
    assert result["service_state"] == "running"


def test_control_project_forbidden_for_non_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        _forbidden_admin_user,
    )

    payload = projects_route.ProjectControlPayload(action="stop")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(projects_route.control_project("benoss", payload, request=object(), db=object()))

    assert exc_info.value.status_code == 403


def test_control_project_returns_500_on_command_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: _User(role="admin"),
    )
    monkeypatch.setattr(projects_route, "run_health_checks", _noop_async)

    def _run_project_control_action(_project_id, _action, **kwargs):
        assert kwargs.get("operator") == "admin"
        return ProjectControlResult(
            project_id="benoss",
            action="stop",
            ok=False,
            service_state="unknown",
            output="command failed",
            exit_code=1,
        )

    monkeypatch.setattr(
        projects_route,
        "run_project_control_action",
        _run_project_control_action,
    )

    payload = projects_route.ProjectControlPayload(action="stop")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(projects_route.control_project("benoss", payload, request=object(), db=object()))

    assert exc_info.value.status_code == 500
    assert "command failed" in str(exc_info.value.detail)


def test_control_project_accepts_benome(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        projects_route,
        "require_admin_session_user_or_403",
        lambda _request, _db: _User(role="admin"),
    )
    monkeypatch.setattr(projects_route, "run_health_checks", _noop_async)

    def _run_project_control_action(_project_id, _action, **kwargs):
        assert kwargs.get("operator") == "admin"
        return ProjectControlResult(
            project_id="benome",
            action="start",
            ok=True,
            service_state="running",
            output="ok",
            exit_code=0,
        )

    monkeypatch.setattr(
        projects_route,
        "run_project_control_action",
        _run_project_control_action,
    )

    payload = projects_route.ProjectControlPayload(action="start")
    result = asyncio.run(projects_route.control_project("benome", payload, request=object(), db=object()))

    assert result["ok"] is True
    assert result["project_id"] == "benome"
