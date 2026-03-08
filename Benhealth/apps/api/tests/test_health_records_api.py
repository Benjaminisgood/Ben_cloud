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


def test_health_record_api_roundtrip(client):
    _login_admin(client)
    created = client.post(
        "/api/health-records",
        json={
            "domain": "exercise",
            "title": "晚上慢跑恢复计划",
            "summary": "连续三周把晚间慢跑恢复成每周三次。",
            "care_status": "active",
            "concern_level": "medium",
            "frequency": "weekly",
            "exercise_name": "慢跑",
            "metric_name": "duration_minutes",
            "metric_value": 35,
            "metric_unit": "min",
            "energy_score": 7,
            "follow_up_plan": "每周日晚复盘一次",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["exercise_name"] == "慢跑"
    assert payload["domain"] == "exercise"
    assert payload["review_status"] == "approved"
    assert payload["created_at"]
    assert payload["reviewed_at"]

    listed = client.get("/api/health-records?domain=exercise&care_status=active")
    assert listed.status_code == 200
    assert listed.json()[0]["metric_name"] == "duration_minutes"

    updated = client.patch(
        f"/api/health-records/{payload['id']}",
        json={"care_status": "stable", "concern_level": "low"},
    )
    assert updated.status_code == 200
    assert updated.json()["care_status"] == "stable"

    deleted = client.delete(f"/api/health-records/{payload['id']}")
    assert deleted.status_code == 204


def test_health_record_requires_admin_review(client):
    _login_user(client)
    created = client.post(
        "/api/health-records",
        json={
            "domain": "diet",
            "title": "午餐后困倦观察",
            "summary": "高碳午餐后两小时困倦明显。",
            "food_name": "米饭套餐",
        },
    )
    assert created.status_code == 201
    assert created.json()["review_status"] == "pending_review"
    assert created.json()["created_at"]
    assert created.json()["reviewed_at"] is None

    updated = client.patch(
        f"/api/health-records/{created.json()['id']}",
        json={"care_status": "needs_attention"},
    )
    assert updated.status_code == 403

    reviewed = client.post(
        f"/api/health-records/{created.json()['id']}/review",
        json={"review_status": "approved", "review_note": "确认纳入正式健康追踪"},
    )
    assert reviewed.status_code == 403

    _login_admin(client)
    reviewed = client.post(
        f"/api/health-records/{created.json()['id']}/review",
        json={"review_status": "approved"},
    )
    assert reviewed.status_code == 200
    payload = reviewed.json()
    assert payload["review_status"] == "approved"
    assert payload["reviewed_by"] == "benbenbuben"
    assert payload["reviewed_at"]


def test_health_record_reject_deletes_record(client):
    _login_user(client)
    created = client.post(
        "/api/health-records",
        json={
            "domain": "habit",
            "title": "熬夜补工作",
            "summary": "连续几天超过一点睡觉。",
        },
    )
    assert created.status_code == 201

    _login_admin(client)
    rejected = client.post(
        f"/api/health-records/{created.json()['id']}/review",
        json={"review_status": "rejected"},
    )
    assert rejected.status_code == 204

    detail = client.get(f"/api/health-records/{created.json()['id']}")
    assert detail.status_code == 404


def test_health_record_web_review_flow(client):
    _login_user(client)
    created = client.post(
        "/api/health-records",
        json={
            "domain": "mental",
            "title": "会议后低能量",
            "summary": "下午长会后恢复速度偏慢。",
        },
    )
    assert created.status_code == 201

    _login_admin(client)
    approved = client.post(
        f"/health-records/{created.json()['id']}/review",
        data={"review_status": "approved"},
        follow_redirects=False,
    )
    assert approved.status_code == 303

    detail = client.get(f"/api/health-records/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["review_status"] == "approved"

    created = client.post(
        "/api/health-records",
        json={
            "domain": "diet",
            "title": "深夜奶茶",
            "summary": "晚上高糖饮料影响睡眠。",
        },
    )
    assert created.status_code == 201

    rejected = client.post(
        f"/health-records/{created.json()['id']}/review",
        data={"review_status": "rejected"},
        follow_redirects=False,
    )
    assert rejected.status_code == 303

    detail = client.get(f"/api/health-records/{created.json()['id']}")
    assert detail.status_code == 404
