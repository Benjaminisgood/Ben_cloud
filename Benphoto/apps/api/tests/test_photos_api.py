
from __future__ import annotations

import benphoto_api.core.config as config_module
import benphoto_api.services.oss_sync as oss_sync_module


def _login(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_photo_api_roundtrip(client):
    _login(client)
    created = client.post(
        "/api/photos",
        json={"title": "狗狗散步", "caption": "傍晚的狗和风", "oss_path": "pets/dog-walk.jpg"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["title"] == "狗狗散步"
    assert payload["image_url"] == "https://00ling.oss-cn-shanghai.aliyuncs.com/benphoto/pets/dog-walk.jpg"

    listed = client.get("/api/photos")
    assert listed.status_code == 200
    assert listed.json()[0]["title"] == "狗狗散步"

    photo_id = payload["id"]
    tossed = client.patch(f"/api/photos/{photo_id}", json={"is_trashed": True})
    assert tossed.status_code == 200
    assert tossed.json()["is_trashed"] is True

    restored = client.patch(f"/api/photos/{photo_id}", json={"is_trashed": False})
    assert restored.status_code == 200
    assert restored.json()["is_trashed"] is False

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["desk_cards"]


def test_photo_api_rejects_duplicate_oss_path(client):
    _login(client)
    payload = {"title": "自拍", "caption": "镜子前", "oss_path": "selfies/mirror.jpg"}

    first = client.post("/api/photos", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/api/photos", json=payload)
    assert duplicate.status_code == 409
    assert duplicate.json() == {"detail": "photo_exists"}


def test_photo_api_normalizes_prefixed_object_key(client):
    _login(client)

    created = client.post(
        "/api/photos",
        json={"title": "海边", "caption": "带前缀录入", "oss_path": "benphoto/trips/seaside.jpg"},
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["oss_path"] == "trips/seaside.jpg"
    assert payload["image_url"] == "https://00ling.oss-cn-shanghai.aliyuncs.com/benphoto/trips/seaside.jpg"

    duplicate = client.post(
        "/api/photos",
        json={"title": "海边重复", "caption": "", "oss_path": "trips/seaside.jpg"},
    )
    assert duplicate.status_code == 409


def test_dashboard_auto_imports_missing_oss_photos(client, monkeypatch):
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_ID", "test-ak")
    monkeypatch.setenv("ALIYUN_OSS_ACCESS_KEY_SECRET", "test-sk")
    config_module.get_settings.cache_clear()
    monkeypatch.setattr(
        oss_sync_module,
        "_list_matching_object_keys",
        lambda settings: ["albums/sunrise.jpg", "albums/sunrise.jpg"],
    )

    _login(client)

    dashboard = client.get("/api/dashboard")
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["summary"][0]["value"] == "1"
    assert payload["desk_cards"][0]["source_label"] == "albums/sunrise.jpg"

    second_dashboard = client.get("/api/dashboard")
    assert second_dashboard.status_code == 200
    assert second_dashboard.json()["summary"][0]["value"] == "1"

    photos = client.get("/api/photos")
    assert photos.status_code == 200
    listed = photos.json()
    assert len(listed) == 1
    assert listed[0]["oss_path"] == "albums/sunrise.jpg"
    assert listed[0]["added_by"] == "oss-sync"
    assert listed[0]["image_url"] == "https://00ling.oss-cn-shanghai.aliyuncs.com/benphoto/albums/sunrise.jpg"
