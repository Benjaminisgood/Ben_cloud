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


def test_dashboard_is_public(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "老电影放映室" in response.text


def test_sso_login_sets_admin_viewer_state(client):
    token = _make_token("agent-user", "admin")
    response = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["viewer"]["is_admin"] is True


def test_non_admin_cannot_patch_video(client):
    token = _make_token("agent-user", "user")
    client.get(f"/auth/sso?token={token}", follow_redirects=False)

    response = client.patch("/api/videos/1", json={"status": "trashed"})
    assert response.status_code == 403
    assert response.json() == {"detail": "admin_required"}
