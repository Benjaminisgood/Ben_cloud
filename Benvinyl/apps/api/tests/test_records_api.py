from __future__ import annotations

import benvinyl_api.core.config as config_module
import benvinyl_api.services.oss_sync as oss_sync_module


def _login(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_records_api_roundtrip(client):
    unauthorized = client.post("/api/records", json={"oss_path": "audio/daybreak.mp3"})
    assert unauthorized.status_code == 401

    _login(client)

    created = client.post(
        "/api/records",
        json={"note": "早晨节目", "oss_path": "audio/daybreak.mp3"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "daybreak"
    assert payload["audio_url"] == "https://media.example.com/audio/daybreak.mp3"
    assert payload["is_trashed"] is False

    duplicate = client.post("/api/records", json={"oss_path": "audio/daybreak.mp3"})
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "record_exists"}

    listed = client.get("/api/records")
    assert listed.status_code == 200
    assert listed.json()[0]["id"] == payload["id"]

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["now_playing"]["id"] == payload["id"]

    trashed = client.patch(f"/api/records/{payload['id']}", json={"is_trashed": True})
    assert trashed.status_code == 200
    assert trashed.json()["is_trashed"] is True

    dashboard_after_trash = client.get("/api/dashboard").json()
    assert dashboard_after_trash["trash_cards"][0]["id"] == payload["id"]

    restored = client.patch(f"/api/records/{payload['id']}", json={"is_trashed": False})
    assert restored.status_code == 200
    assert restored.json()["is_trashed"] is False

    dashboard_after_restore = client.get(f"/api/dashboard?record_id={payload['id']}").json()
    assert dashboard_after_restore["now_playing"]["id"] == payload["id"]

    missing = client.patch("/api/records/9999", json={"is_trashed": True})
    assert missing.status_code == 404
    assert missing.json() == {"detail": "record_not_found"}


def test_records_api_normalizes_prefixed_object_key(client, monkeypatch):
    monkeypatch.setenv("ALIYUN_OSS_PUBLIC_BASE_URL", "https://media.example.com/benvinyl")
    monkeypatch.setenv("ALIYUN_OSS_PREFIX", "benvinyl")
    config_module.get_settings.cache_clear()

    _login(client)

    created = client.post(
        "/api/records",
        json={"note": "夜间节目", "oss_path": "benvinyl/audio/nocturne.mp3"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["oss_path"] == "audio/nocturne.mp3"
    assert payload["audio_url"] == "https://media.example.com/benvinyl/audio/nocturne.mp3"


def test_dashboard_auto_imports_missing_oss_records(client, monkeypatch):
    monkeypatch.setenv("ALIYUN_OSS_ENDPOINT", "oss-cn-shanghai.aliyuncs.com")
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_ID", "test-ak")
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "test-sk")
    monkeypatch.setenv("ALIYUN_OSS_BUCKET", "media-example")
    monkeypatch.setenv("ALIYUN_OSS_PREFIX", "benvinyl")
    config_module.get_settings.cache_clear()
    monkeypatch.setattr(
        oss_sync_module,
        "_list_matching_object_keys",
        lambda settings: ["audio/daybreak.mp3", "audio/daybreak.mp3"],
    )

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["summary"][0]["value"] == "1"
    assert payload["now_playing"]["source_label"] == "audio/daybreak.mp3"

    second_dashboard = client.get("/api/dashboard")
    assert second_dashboard.status_code == 200
    assert second_dashboard.json()["summary"][0]["value"] == "1"

    _login(client)
    records = client.get("/api/records")
    assert records.status_code == 200
    listed = records.json()
    assert len(listed) == 1
    assert listed[0]["oss_path"] == "audio/daybreak.mp3"
    assert listed[0]["added_by"] == "oss-sync"
