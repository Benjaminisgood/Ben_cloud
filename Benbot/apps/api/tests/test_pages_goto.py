from __future__ import annotations

from types import SimpleNamespace

import pytest

from benbot_api.core.config import ProjectConfig
from benbot_api.schemas.web import SessionUserDTO
from benbot_api.services import web_pages


class _Settings:
    def __init__(self, projects: list[ProjectConfig], sso_secret: str = "test-sso-secret") -> None:
        self._projects = projects
        self.SSO_SECRET = sso_secret

    def get_projects(self) -> list[ProjectConfig]:
        return self._projects


def _request(*, scheme: str = "http", hostname: str = "portal.local") -> SimpleNamespace:
    return SimpleNamespace(url=SimpleNamespace(scheme=scheme, hostname=hostname, path="/goto/benoss"))


def _project(*, public_url: str, sso_enabled: bool = True) -> ProjectConfig:
    return ProjectConfig(
        id="benoss",
        name="Benoss",
        description="desc",
        icon="book",
        port=8000,
        internal_url="http://localhost:8000",
        public_url=public_url,
        sso_entry_path="/auth/sso",
        sso_enabled=sso_enabled,
    )


def _user() -> SessionUserDTO:
    return SessionUserDTO(id=1, username="admin", role="admin", is_active=True)


def _normal_user() -> SessionUserDTO:
    return SessionUserDTO(id=2, username="alice", role="user", is_active=True)


def test_goto_project_uses_current_host_and_ignores_public_url_host_path_and_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _Settings([_project(public_url="https://apps.example.com/benoss?src=portal")])

    monkeypatch.setattr(web_pages, "get_settings", lambda: settings)
    monkeypatch.setattr(web_pages, "create_sso_token", lambda *_args, **_kwargs: "signed-token=")
    monkeypatch.setattr(web_pages, "record_click", lambda _db, _project_id: None)

    target = web_pages.assemble_project_redirect_target(
        project_id="benoss",
        request=_request(hostname="ignored.local"),
        db=object(),
        current_user=_user(),
    )

    assert target is not None
    assert target.redirect_url == "http://ignored.local:8000/auth/sso?token=signed-token%3D"


def test_goto_project_falls_back_to_current_host_when_public_url_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _Settings([_project(public_url="")])

    monkeypatch.setattr(web_pages, "get_settings", lambda: settings)
    monkeypatch.setattr(web_pages, "create_sso_token", lambda *_args, **_kwargs: "signed-token=")
    monkeypatch.setattr(web_pages, "record_click", lambda _db, _project_id: None)

    target = web_pages.assemble_project_redirect_target(
        project_id="benoss",
        request=_request(hostname="127.0.0.1"),
        db=object(),
        current_user=_user(),
    )

    assert target is not None
    assert target.redirect_url == "http://127.0.0.1:8000/auth/sso?token=signed-token%3D"


def test_goto_project_without_sso_does_not_append_token(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _Settings([_project(public_url="https://apps.example.com/benoss", sso_enabled=False)])

    monkeypatch.setattr(web_pages, "get_settings", lambda: settings)
    monkeypatch.setattr(web_pages, "record_click", lambda _db, _project_id: None)

    target = web_pages.assemble_project_redirect_target(
        project_id="benoss",
        request=_request(),
        db=object(),
        current_user=_user(),
    )

    assert target is not None
    assert target.redirect_url == "http://portal.local:8000/auth/sso"


def test_goto_project_keeps_ip_host_and_changes_only_port(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _Settings([_project(public_url="https://apps.example.com")])

    monkeypatch.setattr(web_pages, "get_settings", lambda: settings)
    monkeypatch.setattr(web_pages, "create_sso_token", lambda *_args, **_kwargs: "signed-token=")
    monkeypatch.setattr(web_pages, "record_click", lambda _db, _project_id: None)

    target = web_pages.assemble_project_redirect_target(
        project_id="benoss",
        request=_request(hostname="127.0.0.1"),
        db=object(),
        current_user=_user(),
    )

    assert target is not None
    assert target.redirect_url == "http://127.0.0.1:8000/auth/sso?token=signed-token%3D"


def test_goto_project_forbidden_when_user_has_no_project_access(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = _Settings([_project(public_url="https://apps.example.com/benoss")])

    monkeypatch.setattr(web_pages, "get_settings", lambda: settings)
    monkeypatch.setattr(web_pages, "can_user_access_project", lambda **_kwargs: False)
    monkeypatch.setattr(web_pages, "record_click", lambda _db, _project_id: None)

    with pytest.raises(PermissionError):
        web_pages.assemble_project_redirect_target(
            project_id="benoss",
            request=_request(),
            db=object(),
            current_user=_normal_user(),
        )
