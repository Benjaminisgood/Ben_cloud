from __future__ import annotations

import benreel_api.core.config as config_module
import benreel_api.services.programming as programming_module


def _login(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_dashboard_program_is_limited(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["summary"][1]["value"] == "2"
    assert len(payload["program"]) == 2


def test_trash_listing_requires_admin(client):
    response = client.get("/api/videos", params={"status": "trashed"})
    assert response.status_code == 403
    assert response.json() == {"detail": "admin_required"}


def test_admin_can_trash_and_restore_video(client):
    initial_program = client.get("/api/dashboard").json()["program"]
    target_id = initial_program[0]["id"]

    unauthorized = client.patch(f"/api/videos/{target_id}", json={"status": "trashed"})
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "auth_required"}

    _login(client)

    trashed = client.patch(f"/api/videos/{target_id}", json={"status": "trashed"})
    assert trashed.status_code == 200
    assert trashed.json()["status"] == "trashed"

    dashboard_after_trash = client.get("/api/dashboard").json()
    assert all(item["id"] != target_id for item in dashboard_after_trash["program"])

    trash_list = client.get("/api/videos", params={"status": "trashed"})
    assert trash_list.status_code == 200
    assert any(item["id"] == target_id for item in trash_list.json())

    restored = client.patch(f"/api/videos/{target_id}", json={"status": "active"})
    assert restored.status_code == 200
    assert restored.json()["status"] == "active"

    dashboard_after_restore = client.get("/api/dashboard").json()
    assert any(item["id"] == target_id for item in dashboard_after_restore["program"])


def test_dashboard_auto_imports_missing_oss_videos(client, monkeypatch):
    monkeypatch.setenv("ALIYUN_OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_ID", "test-ak")
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "test-sk")
    monkeypatch.setenv("ALIYUN_OSS_BUCKET", "oss-example")
    monkeypatch.setenv("ALIYUN_OSS_PREFIX", "videos")
    config_module.get_settings.cache_clear()
    monkeypatch.setattr(
        programming_module,
        "_list_matching_object_keys",
        lambda settings: ["videos/midnight-train.mp4", "videos/silver-moon.mp4"],
    )

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["summary"][0]["value"] == "4"

    videos = client.get("/api/videos")
    assert videos.status_code == 200
    listed = videos.json()
    assert len(listed) == 4

    imported = [item for item in listed if item["asset_url"].endswith("/videos/silver-moon.mp4")]
    assert len(imported) == 1
    assert imported[0]["title"] == "silver moon"
    assert imported[0]["poster_url"] is None

    repeated = client.get("/api/videos")
    assert repeated.status_code == 200
    assert len(repeated.json()) == 4
