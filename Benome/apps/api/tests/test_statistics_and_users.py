from __future__ import annotations


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
