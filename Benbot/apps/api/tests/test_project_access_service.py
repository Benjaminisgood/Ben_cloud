from __future__ import annotations

from dataclasses import dataclass

import pytest

from benbot_api.core.config import ProjectConfig
from benbot_api.schemas.web import SessionUserDTO
from benbot_api.services import project_access


@dataclass
class _User:
    id: int
    username: str
    role: str


def _project(project_id: str) -> ProjectConfig:
    return ProjectConfig(
        id=project_id,
        name=project_id.upper(),
        description="desc",
        icon="book",
        port=8000,
        internal_url="http://localhost:8000",
        public_url="",
        sso_entry_path="/auth/sso",
        sso_enabled=True,
    )


def test_filter_visible_projects_for_non_admin_uses_allowlist(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_access, "list_project_ids_for_user", lambda _db, _user_id: ["benlab"])
    visible = project_access.filter_visible_projects_for_user(
        db=object(),
        current_user=SessionUserDTO(id=2, username="alice", role="user", is_active=True),
        projects=[_project("benoss"), _project("benlab")],
    )
    assert [project.id for project in visible] == ["benlab"]


def test_update_user_project_access_rejects_admin_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(project_access, "get_user_by_id", lambda _db, _user_id: _User(1, "admin", "admin"))
    with pytest.raises(ValueError, match="admin_access_fixed"):
        project_access.update_user_project_access(
            db=object(),
            operator="root",
            user_id=1,
            project_ids=["benoss"],
        )


def test_update_user_project_access_normalizes_and_returns_change_id(monkeypatch: pytest.MonkeyPatch) -> None:
    target_user = _User(7, "alice", "user")
    captured: dict[str, list[str]] = {}

    monkeypatch.setattr(project_access, "get_user_by_id", lambda _db, _user_id: target_user)
    monkeypatch.setattr(project_access, "_known_project_ids", lambda: {"benoss", "benlab"})
    monkeypatch.setattr(
        project_access,
        "replace_user_project_access",
        lambda _db, *, user_id, project_ids, granted_by: captured.update(
            {"project_ids": list(project_ids), "user_id": [user_id], "granted_by": [granted_by]}
        ),
    )
    monkeypatch.setattr(project_access, "_create_access_change_log", lambda **_kwargs: 77)

    user, project_ids, change_id = project_access.update_user_project_access(
        db=object(),
        operator="root",
        user_id=7,
        project_ids=["BENLAB", " benoss ", "benlab"],
    )

    assert user.username == "alice"
    assert project_ids == ["benlab", "benoss"]
    assert change_id == 77
    assert captured["project_ids"] == ["benlab", "benoss"]
