from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from benome_api.core.config import get_settings


def _login_admin(client):
    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "linghome123"},
    )
    assert response.status_code == 200
    return response.json()["user_id"]


def _register_customer(client, username: str, phone: str):
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "customer123",
            "full_name": username,
            "phone": phone,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def test_statistics_requires_admin_and_tracks_pending_review(client):
    admin_id = _login_admin(client)

    create_property = client.post(
        "/api/admin/properties",
        headers={"X-User-Id": str(admin_id)},
        json={
            "title": "统计测试房源",
            "description": "用于统计测试",
            "city": "上海",
            "address": "浦东新区 100 号",
            "price_per_night": 499,
            "max_guests": 2,
            "is_active": True,
        },
    )
    assert create_property.status_code == 201
    property_id = create_property.json()["id"]

    customer_id = _register_customer(client, "stats_customer", "13100000001")

    create_booking = client.post(
        "/api/bookings",
        headers={"X-User-Id": str(customer_id)},
        json={
            "property_id": property_id,
            "check_in_date": "2026-03-15",
            "check_out_date": "2026-03-16",
            "guest_count": 1,
            "guest_name": "客户A",
            "guest_phone": "13100000001",
            "note": "统计用订单",
        },
    )
    assert create_booking.status_code == 201
    assert create_booking.json()["status"] == "pending_review"

    overview = client.get("/api/statistics/overview", headers={"X-User-Id": str(admin_id)})
    assert overview.status_code == 200
    assert overview.json()["pending_bookings"] >= 1

    invalid_days = client.get("/api/statistics/bookings?days=0", headers={"X-User-Id": str(admin_id)})
    assert invalid_days.status_code == 400

    forbidden = client.get("/api/statistics/overview", headers={"X-User-Id": str(customer_id)})
    assert forbidden.status_code == 403


def test_users_profile_and_password_flow(client):
    customer_id = _register_customer(client, "profile_user", "13100000002")

    me = client.get("/api/users/me", headers={"X-User-Id": str(customer_id)})
    assert me.status_code == 200
    assert me.json()["username"] == "profile_user"
    assert "email" not in me.json()

    update_profile = client.put(
        "/api/users/me",
        headers={"X-User-Id": str(customer_id)},
        json={"full_name": "Profile User", "phone": "13111112222"},
    )
    assert update_profile.status_code == 200
    assert update_profile.json()["full_name"] == "Profile User"
    assert update_profile.json()["phone"] == "13111112222"

    wrong_password = client.post(
        "/api/users/me/change-password",
        headers={"X-User-Id": str(customer_id)},
        json={
            "old_password": "bad-password",
            "new_password": "new-password-123",
            "confirm_password": "new-password-123",
        },
    )
    assert wrong_password.status_code == 400

    change_password = client.post(
        "/api/users/me/change-password",
        headers={"X-User-Id": str(customer_id)},
        json={
            "old_password": "customer123",
            "new_password": "new-password-123",
            "confirm_password": "new-password-123",
        },
    )
    assert change_password.status_code == 200

    login_with_new_password = client.post(
        "/api/auth/login",
        json={"username": "profile_user", "password": "new-password-123"},
    )
    assert login_with_new_password.status_code == 200


def _build_sso_token(username: str, role: str = "admin") -> str:
    payload = {
        "u": username,
        "r": role,
        "e": int(time.time()) + 60,
        "n": secrets.token_hex(8),
    }
    data = json.dumps(payload, separators=(",", ":"))
    signature = hmac.new(
        get_settings().SSO_SECRET.encode(),
        data.encode(),
        hashlib.sha256,
    ).hexdigest()
    return base64.urlsafe_b64encode(f"{data}.{signature}".encode()).decode()


def test_admin_settings_and_system_info_api(client):
    admin_id = _login_admin(client)

    system_info = client.get("/api/system/info", headers={"X-User-Id": str(admin_id)})
    assert system_info.status_code == 200
    assert "version" in system_info.json()
    assert "python_version" in system_info.json()

    save_settings = client.post(
        "/api/admin/settings",
        headers={"X-User-Id": str(admin_id)},
        json={
            "platform_name": "Benome Test",
            "currency": "CNY",
            "max_advance_days": 120,
            "min_nights": 2,
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "email_notifications": "enabled",
            "sms_notifications": "disabled",
        },
    )
    assert save_settings.status_code == 200
    assert save_settings.json()["ok"] is True
    assert save_settings.json()["settings"]["platform_name"] == "Benome Test"

    fetch_settings = client.get("/api/admin/settings", headers={"X-User-Id": str(admin_id)})
    assert fetch_settings.status_code == 200
    assert fetch_settings.json()["settings"]["max_advance_days"] == 120


def test_admin_pages_render_with_sso_session(client):
    token = _build_sso_token("admin", role="admin")
    sso = client.get("/auth/sso", params={"token": token})
    assert sso.status_code == 200

    users_page = client.get("/admin/users")
    assert users_page.status_code == 200
    assert "用户管理" in users_page.text

    bookings_page = client.get("/admin/bookings")
    assert bookings_page.status_code == 200
    assert "预订管理" in bookings_page.text
