from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.responses import RedirectResponse

from benbot_api.schemas.web import ApiTokenUserDTO, SessionUserDTO
from benbot_api.web import deps


def _request(path: str = "/") -> SimpleNamespace:
    return SimpleNamespace(
        session={},
        url=SimpleNamespace(path=path),
        headers={},
        client=SimpleNamespace(host="127.0.0.1"),
    )


def test_get_session_user_returns_dto(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request()
    request.session["user_id"] = 11
    fake_user = SimpleNamespace(id=11, username="ben", role="admin", is_active=True)
    monkeypatch.setattr(deps, "get_user_by_id", lambda _db, _user_id: fake_user)

    user = deps.get_session_user(request, db=object())
    assert isinstance(user, SessionUserDTO)
    assert user.id == 11
    assert user.username == "ben"


def test_require_session_user_or_redirect_redirects_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_session_user", lambda _request, _db: None)
    result = deps.require_session_user_or_redirect(_request("/goto/benoss"), db=object())
    assert isinstance(result, RedirectResponse)
    assert result.headers["location"] == "/login?next=/goto/benoss"


def test_require_guest_or_redirect_home_redirects_when_logged_in(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        deps,
        "get_session_user",
        lambda _request, _db: SessionUserDTO(id=1, username="ben", role="admin", is_active=True),
    )
    result = deps.require_guest_or_redirect_home(_request("/login"), db=object())
    assert isinstance(result, RedirectResponse)
    assert result.headers["location"] == "/"


def test_require_session_user_or_401_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_session_user", lambda _request, _db: None)
    with pytest.raises(HTTPException) as exc_info:
        deps.require_session_user_or_401(_request("/api/projects/status"), db=object())
    assert exc_info.value.status_code == 401


def test_require_admin_session_user_or_403_raises_for_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        deps,
        "get_session_user",
        lambda _request, _db: SessionUserDTO(id=2, username="user", role="user", is_active=True),
    )
    with pytest.raises(HTTPException) as exc_info:
        deps.require_admin_session_user_or_403(_request("/api/projects/status"), db=object())
    assert exc_info.value.status_code == 403


def test_require_admin_principal_or_401_accepts_api_token_user(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_session_user", lambda _request, _db: None)
    monkeypatch.setattr(
        deps,
        "get_api_token_user",
        lambda _request, _db: ApiTokenUserDTO(scopes={"bug_repair:read"}),
    )
    principal = deps.require_admin_principal_or_401(
        _request("/api/bugs/unrepaired"),
        db=object(),
        required_scope="bug_repair:read",
    )
    assert isinstance(principal, ApiTokenUserDTO)
