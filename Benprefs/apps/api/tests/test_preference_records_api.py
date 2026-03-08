from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def _login_admin(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def _login_user(client):
    payload = {"u": "agent-user", "r": "user", "e": int(time.time()) + 30, "n": "abcdef12"}
    data = json.dumps(payload, separators=(",", ":"), ensure_ascii=False)
    sig = hmac.new(b"test-sso-secret", data.encode(), hashlib.sha256).hexdigest()
    token = base64.urlsafe_b64encode(f"{data}.{sig}".encode()).decode()
    response = client.get(f"/auth/sso?token={token}", follow_redirects=False)
    assert response.status_code == 303


def test_preference_record_api_roundtrip(client):
    _login_admin(client)
    created = client.post(
        "/api/preference-records",
        json={
            "subject_type": "food",
            "subject_name": "热干面",
            "aspect": "早餐满足感",
            "stance": "like",
            "timeframe": "current",
            "validation_state": "confirmed",
            "intensity": 8,
            "certainty": 7,
            "context": "工作日早晨",
            "merchant_name": "小区门口早餐店",
            "source_kind": "manual",
            "trigger_detail": "高压早晨更想吃热食",
            "supporting_detail": "连续两周都主动选择",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["subject_name"] == "热干面"
    assert payload["stance"] == "like"
    assert payload["review_status"] == "approved"
    assert payload["created_at"]
    assert payload["reviewed_at"]

    listed = client.get("/api/preference-records?subject_type=food&stance=like")
    assert listed.status_code == 200
    assert listed.json()[0]["validation_state"] == "confirmed"

    updated = client.patch(
        f"/api/preference-records/{payload['id']}",
        json={"validation_state": "retired", "certainty": 5},
    )
    assert updated.status_code == 200
    assert updated.json()["validation_state"] == "retired"

    deleted = client.delete(f"/api/preference-records/{payload['id']}")
    assert deleted.status_code == 204


def test_preference_record_requires_admin_review(client):
    _login_user(client)
    created = client.post(
        "/api/preference-records",
        json={
            "subject_type": "merchant",
            "subject_name": "深夜便利店",
            "aspect": "服务节奏",
            "stance": "avoid",
            "timeframe": "current",
        },
    )
    assert created.status_code == 201
    assert created.json()["review_status"] == "pending_review"
    assert created.json()["created_at"]
    assert created.json()["reviewed_at"] is None

    updated = client.patch(
        f"/api/preference-records/{created.json()['id']}",
        json={"validation_state": "confirmed"},
    )
    assert updated.status_code == 403

    reviewed = client.post(
        f"/api/preference-records/{created.json()['id']}/review",
        json={"review_status": "approved", "review_note": "确认可录入正式偏好库"},
    )
    assert reviewed.status_code == 403

    _login_admin(client)
    reviewed = client.post(
        f"/api/preference-records/{created.json()['id']}/review",
        json={"review_status": "approved"},
    )
    assert reviewed.status_code == 200
    payload = reviewed.json()
    assert payload["review_status"] == "approved"
    assert payload["reviewed_by"] == "benbenbuben"
    assert payload["reviewed_at"]


def test_preference_record_reject_deletes_record(client):
    _login_user(client)
    created = client.post(
        "/api/preference-records",
        json={
            "subject_type": "activity",
            "subject_name": "凌晨健身房",
            "aspect": "恢复节奏",
            "stance": "avoid",
            "timeframe": "current",
        },
    )
    assert created.status_code == 201

    _login_admin(client)
    rejected = client.post(
        f"/api/preference-records/{created.json()['id']}/review",
        json={"review_status": "rejected"},
    )
    assert rejected.status_code == 204

    detail = client.get(f"/api/preference-records/{created.json()['id']}")
    assert detail.status_code == 404


def test_preference_record_web_review_flow(client):
    _login_user(client)
    created = client.post(
        "/api/preference-records",
        json={
            "subject_type": "food",
            "subject_name": "抹茶酸奶",
            "aspect": "下午加餐",
            "stance": "curious",
            "timeframe": "future",
        },
    )
    assert created.status_code == 201

    _login_admin(client)
    approved = client.post(
        f"/preference-records/{created.json()['id']}/review",
        data={"review_status": "approved"},
        follow_redirects=False,
    )
    assert approved.status_code == 303

    detail = client.get(f"/api/preference-records/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "approved"

    created = client.post(
        "/api/preference-records",
        json={
            "subject_type": "habit",
            "subject_name": "通宵追剧",
            "aspect": "睡前安排",
            "stance": "avoid",
            "timeframe": "current",
        },
    )
    assert created.status_code == 201

    rejected = client.post(
        f"/preference-records/{created.json()['id']}/review",
        data={"review_status": "rejected"},
        follow_redirects=False,
    )
    assert rejected.status_code == 303

    detail = client.get(f"/api/preference-records/{created.json()['id']}")
    assert detail.status_code == 404
