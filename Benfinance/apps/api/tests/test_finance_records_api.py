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


def test_finance_record_api_roundtrip(client):
    _login_admin(client)
    created = client.post(
        "/api/finance-records",
        json={
            "record_type": "bill",
            "title": "季度保险费",
            "description": "记录季度车险支出和续费决策。",
            "category": "insurance",
            "flow_direction": "outflow",
            "planning_status": "pending",
            "risk_level": "medium",
            "amount": 2450.5,
            "currency": "CNY",
            "account_name": "招商银行卡",
            "counterparty": "平安保险",
            "follow_up_action": "到期前两周比较报价",
        },
    )
    assert created.status_code == 201
    payload = created.json()
    assert payload["record_type"] == "bill"
    assert payload["amount"] == 2450.5
    assert payload["review_status"] == "approved"
    assert payload["created_at"]
    assert payload["reviewed_at"]

    listed = client.get("/api/finance-records?record_type=bill&planning_status=pending")
    assert listed.status_code == 200
    assert listed.json()[0]["category"] == "insurance"

    updated = client.patch(
        f"/api/finance-records/{payload['id']}",
        json={"planning_status": "active", "risk_level": "low"},
    )
    assert updated.status_code == 200
    assert updated.json()["planning_status"] == "active"

    deleted = client.delete(f"/api/finance-records/{payload['id']}")
    assert deleted.status_code == 204


def test_finance_record_requires_admin_review(client):
    _login_user(client)
    created = client.post(
        "/api/finance-records",
        json={
            "record_type": "decision",
            "title": "是否继续保留高额会员",
            "description": "评估是否保留当前订阅。",
            "category": "subscription",
        },
    )
    assert created.status_code == 201
    assert created.json()["review_status"] == "pending_review"
    assert created.json()["created_at"]
    assert created.json()["reviewed_at"] is None

    updated = client.patch(
        f"/api/finance-records/{created.json()['id']}",
        json={"planning_status": "cancelled"},
    )
    assert updated.status_code == 403

    reviewed = client.post(
        f"/api/finance-records/{created.json()['id']}/review",
        json={"review_status": "approved", "review_note": "确认纳入正式财务记录"},
    )
    assert reviewed.status_code == 403

    _login_admin(client)
    reviewed = client.post(
        f"/api/finance-records/{created.json()['id']}/review",
        json={"review_status": "approved", "review_note": "确认纳入正式财务记录"},
    )
    assert reviewed.status_code == 200
    payload = reviewed.json()
    assert payload["review_status"] == "approved"
    assert payload["review_note"] == "确认纳入正式财务记录"
    assert payload["reviewed_by"] == "benbenbuben"
    assert payload["reviewed_at"]
