from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from benbot_api.api.routes import admin_users


def test_get_user_project_access_overview_includes_admin_as_full_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        admin_users,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        admin_users,
        "assemble_user_project_access_overview",
        lambda **_kwargs: SimpleNamespace(
            projects=[
                SimpleNamespace(id="benoss", name="Benoss"),
                SimpleNamespace(id="benlab", name="Benlab"),
            ],
            users=[
                SimpleNamespace(id=1, username="root", role="admin", is_active=True),
                SimpleNamespace(id=2, username="alice", role="user", is_active=True),
            ],
            access_map={2: ["benlab"]},
        ),
    )

    response = admin_users.get_user_project_access_overview(request=object(), db=object())

    assert len(response.projects) == 2
    assert response.users[0].project_ids == ["benoss", "benlab"]
    assert response.users[1].project_ids == ["benlab"]


def test_put_user_project_access_returns_change_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_users,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        admin_users,
        "update_user_project_access",
        lambda **_kwargs: (SimpleNamespace(id=2), ["benoss"], 901),
    )

    response = admin_users.put_user_project_access(
        user_id=2,
        payload=admin_users.UserProjectAccessUpdatePayload(project_ids=["benoss"]),
        request=object(),
        db=object(),
    )

    assert response.ok is True
    assert response.user_id == 2
    assert response.project_ids == ["benoss"]
    assert response.change_id == 901


def test_put_user_project_access_rejects_admin_target(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        admin_users,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        admin_users,
        "update_user_project_access",
        lambda **_kwargs: (_ for _ in ()).throw(ValueError("admin_access_fixed")),
    )

    with pytest.raises(HTTPException) as exc_info:
        admin_users.put_user_project_access(
            user_id=1,
            payload=admin_users.UserProjectAccessUpdatePayload(project_ids=[]),
            request=object(),
            db=object(),
        )
    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "admin_access_fixed"
