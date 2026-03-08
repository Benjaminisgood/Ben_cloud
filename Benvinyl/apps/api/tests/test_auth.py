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


def test_login_page_available(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Benvinyl" in response.text


def test_sso_login_allows_admin_write(client):
    token = _make_token("agent-user", "admin")
    response = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    created = client.post(
        "/api/records",
        json={"title": "Night Radio", "note": "SSO 创建", "oss_path": "audio/night-radio.mp3"},
    )
    assert created.status_code == 201
    assert created.json()["added_by"] == "agent-user"
