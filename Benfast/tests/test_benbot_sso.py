"""Benbot SSO integration tests for Benfast."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

from httpx import AsyncClient

from models.admin import User
from settings import settings


def _build_sso_token(*, secret: str, username: str, role: str = "user") -> str:
    payload = {
        "u": username,
        "r": role,
        "e": int(time.time()) + 30,
        "n": "deadbeefcafebabe",
    }
    data = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    raw = f"{data}.{signature}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


class TestBenbotSso:
    async def test_root_health_endpoint(self, async_client: AsyncClient) -> None:
        response = await async_client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["service"] == "Benfast"

    async def test_sso_login_sets_cookie_and_creates_user(
        self, async_client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "SSO_SECRET", "test-benbot-sso", raising=False)
        monkeypatch.setattr(settings, "SSO_REDIRECT_PATH", "/", raising=False)

        token = _build_sso_token(
            secret=settings.SSO_SECRET,
            username="portal_admin",
            role="admin",
        )

        response = await async_client.get(
            "/auth/sso",
            params={"token": token},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert response.headers["location"] == "/"

        cookie_header = "; ".join(response.headers.get_list("set-cookie"))
        assert settings.SSO_TOKEN_COOKIE_NAME in cookie_header
        assert settings.SSO_REFRESH_COOKIE_NAME in cookie_header

        user = await User.filter(username="portal_admin").first()
        assert user is not None
        assert user.is_superuser is True
        assert user.is_active is True

    async def test_sso_login_uses_safe_next_path_when_provided(
        self, async_client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "SSO_SECRET", "test-benbot-sso", raising=False)
        monkeypatch.setattr(settings, "SSO_REDIRECT_PATH", "/", raising=False)

        token = _build_sso_token(
            secret=settings.SSO_SECRET,
            username="portal_user",
        )

        response = await async_client.get(
            "/auth/sso",
            params={"token": token, "next": "/app/"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/app/"

    async def test_sso_login_rejects_unsafe_next_path(
        self, async_client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "SSO_SECRET", "test-benbot-sso", raising=False)
        monkeypatch.setattr(settings, "SSO_REDIRECT_PATH", "/", raising=False)

        token = _build_sso_token(
            secret=settings.SSO_SECRET,
            username="portal_user",
        )

        response = await async_client.get(
            "/auth/sso",
            params={"token": token, "next": "https://evil.example/steal"},
            follow_redirects=False,
        )

        assert response.status_code == 302
        assert response.headers["location"] == "/"

    async def test_sso_rejects_invalid_token(
        self, async_client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "SSO_SECRET", "test-benbot-sso", raising=False)
        response = await async_client.get("/auth/sso", params={"token": "bad-token"})
        assert response.status_code == 401

    async def test_sso_rejects_when_secret_missing(
        self, async_client: AsyncClient, monkeypatch
    ) -> None:
        monkeypatch.setattr(settings, "SSO_SECRET", "", raising=False)
        token = _build_sso_token(secret="unused-secret", username="portal_user")

        response = await async_client.get("/auth/sso", params={"token": token})
        assert response.status_code == 503
