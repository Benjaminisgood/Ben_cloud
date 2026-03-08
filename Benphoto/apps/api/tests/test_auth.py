
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _make_token(username: str, role: str) -> str:
    payload = {"u": username, "r": role, "e": int(time.time()) + 30, "n": "abcdef12"}
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(b"test-sso-secret", data.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{data}.{sig}".encode()).decode()


def test_dashboard_requires_login(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_sso_login_allows_dashboard_access(client):
    token = _make_token("agent-user", "admin")
    response = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["source"] == "Aliyun OSS"
    assert dashboard.json()["daily_limit"] == 6
