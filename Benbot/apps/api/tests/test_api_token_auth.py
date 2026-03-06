from __future__ import annotations

from types import SimpleNamespace

import pytest

from benbot_api.schemas.web import ApiTokenUserDTO
from benbot_api.web import deps


class _Settings:
    NANOBOT_API_TOKEN = "secret-token"

    @property
    def nanobot_allowed_ips_set(self) -> set[str]:
        return {"127.0.0.1"}

    @property
    def nanobot_api_scope_set(self) -> set[str]:
        return {"bug_repair:read", "bug_repair:write"}


def _request(*, token: str, host: str = "127.0.0.1") -> SimpleNamespace:
    return SimpleNamespace(headers={"X-API-Token": token}, client=SimpleNamespace(host=host))


def test_api_token_auth_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: _Settings())
    user = deps.get_api_token_user(_request(token="secret-token"), db=object())
    assert isinstance(user, ApiTokenUserDTO)
    assert user.username == "nanobot"
    assert user.has_scope("bug_repair:write")


def test_api_token_auth_rejects_bad_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: _Settings())
    user = deps.get_api_token_user(_request(token="wrong-token"), db=object())
    assert user is None


def test_api_token_auth_rejects_disallowed_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(deps, "get_settings", lambda: _Settings())
    user = deps.get_api_token_user(_request(token="secret-token", host="10.1.2.3"), db=object())
    assert user is None
