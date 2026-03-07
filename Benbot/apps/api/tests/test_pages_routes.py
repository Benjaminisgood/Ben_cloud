from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi.responses import RedirectResponse

from benbot_api.schemas.web import SessionUserDTO
from benbot_api.web.routes import pages


def _request(path: str = "/manage") -> SimpleNamespace:
    return SimpleNamespace(
        session={},
        url=SimpleNamespace(path=path),
    )


def test_manage_redirects_anonymous_user_to_login(monkeypatch: pytest.MonkeyPatch) -> None:
    redirect = RedirectResponse("/login?next=/manage", status_code=302)
    monkeypatch.setattr(pages, "require_session_user_or_redirect", lambda _request, _db: redirect)

    response = pages.manage(request=_request(), db=object())

    assert response is redirect


def test_manage_redirects_non_admin_back_home_with_flash(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, str]] = []
    monkeypatch.setattr(
        pages,
        "require_session_user_or_redirect",
        lambda _request, _db: SessionUserDTO(id=2, username="alice", role="user", is_active=True),
    )
    monkeypatch.setattr(
        pages,
        "flash",
        lambda _request, message, category="info": captured.append((message, category)),
    )

    response = pages.manage(request=_request(), db=object())

    assert response.status_code == 302
    assert response.headers["location"] == "/"
    assert captured == [("仅管理员可访问管理页", "error")]


def test_manage_renders_management_template_for_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _request()
    admin = SessionUserDTO(id=1, username="root", role="admin", is_active=True)
    monkeypatch.setattr(pages, "require_session_user_or_redirect", lambda _request, _db: admin)
    monkeypatch.setattr(pages, "pop_flash", lambda _request: [["success", "saved"]])
    monkeypatch.setattr(
        pages,
        "assemble_management_page_context",
        lambda **_kwargs: SimpleNamespace(
            to_template_context=lambda: {"title": "Benbot · 管理页", "page": "manage", "current_user": admin},
        ),
    )

    rendered: dict[str, object] = {}

    def _render(_request, name: str, context: dict) -> dict:
        rendered["request"] = _request
        rendered["name"] = name
        rendered["context"] = context
        return rendered

    monkeypatch.setattr(pages, "render_template", _render)

    response = pages.manage(request=request, db=object())

    assert response is rendered
    assert rendered["name"] == "manage.html"
    assert rendered["context"]["page"] == "manage"
