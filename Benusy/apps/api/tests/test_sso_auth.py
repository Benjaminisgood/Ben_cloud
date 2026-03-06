from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _create_sso_token(secret: str, username: str, role: str) -> str:
    payload = {
        "u": username,
        "r": role,
        "e": int(time.time()) + 60,
        "n": "testnonce",
    }
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    raw = f"{data}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def test_session_auth_requires_login(client):
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_sso_login_sets_session_and_allows_api_access(client):
    token = _create_sso_token("test-sso-secret", "portal-admin", "admin")
    callback = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert callback.status_code == 302
    assert callback.headers["location"] == "/admin/dashboard"

    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["username"] == "portal-admin"
    assert payload["role"] == "admin"


def test_sso_login_redirects_blogger_to_dashboard(client):
    token = _create_sso_token("test-sso-secret", "portal-blogger", "blogger")
    callback = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert callback.status_code == 302
    assert callback.headers["location"] == "/dashboard"

    me = client.get("/api/v1/users/me")
    assert me.status_code == 200
    payload = me.json()
    assert payload["username"] == "portal-blogger"
    assert payload["role"] == "blogger"
