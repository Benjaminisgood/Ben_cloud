from __future__ import annotations


def test_booking_review_and_date_lock(client):
    login_admin = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "linghome123"},
    )
    assert login_admin.status_code == 200
    admin_id = login_admin.json()["user_id"]

    create_property = client.post(
        "/api/admin/properties",
        headers={"X-User-Id": str(admin_id)},
        json={
            "title": "市中心亲子套房",
            "description": "步行可达地铁",
            "city": "杭州",
            "address": "西湖区 88 号",
            "price_per_night": 680,
            "max_guests": 4,
            "is_active": True,
        },
    )
    assert create_property.status_code == 201
    property_id = create_property.json()["id"]

    register_customer_1 = client.post(
        "/api/auth/register",
        json={
            "username": "customer_one",
            "password": "customer123",
            "full_name": "Tom",
            "phone": "13000000001",
        },
    )
    assert register_customer_1.status_code == 201
    customer_1_id = register_customer_1.json()["id"]

    booking_1 = client.post(
        "/api/bookings",
        headers={"X-User-Id": str(customer_1_id)},
        json={
            "property_id": property_id,
            "check_in_date": "2026-03-10",
            "check_out_date": "2026-03-12",
            "guest_count": 2,
            "guest_name": "Tom",
            "guest_phone": "13000000001",
            "note": "希望安静房间",
        },
    )
    assert booking_1.status_code == 201
    booking_1_id = booking_1.json()["id"]
    assert booking_1.json()["status"] == "pending_review"
    assert booking_1.json()["total_nights"] == 2

    pending = client.get(
        "/api/admin/bookings/pending",
        headers={"X-User-Id": str(admin_id)},
    )
    assert pending.status_code == 200
    assert len(pending.json()) == 1

    approve_without_payment = client.patch(
        f"/api/admin/bookings/{booking_1_id}/review",
        headers={"X-User-Id": str(admin_id)},
        json={"approve": True, "payment_received": False, "review_note": "未到账"},
    )
    assert approve_without_payment.status_code == 400

    approve_with_payment = client.patch(
        f"/api/admin/bookings/{booking_1_id}/review",
        headers={"X-User-Id": str(admin_id)},
        json={"approve": True, "payment_received": True, "review_note": "已到账"},
    )
    assert approve_with_payment.status_code == 200
    assert approve_with_payment.json()["status"] == "confirmed"

    availability_conflict = client.get(
        f"/api/properties/{property_id}/availability",
        params={"check_in_date": "2026-03-11", "check_out_date": "2026-03-13"},
    )
    assert availability_conflict.status_code == 200
    assert availability_conflict.json()["available"] is False
    assert availability_conflict.json()["conflict_dates"] == ["2026-03-11"]

    availability_checkout_day = client.get(
        f"/api/properties/{property_id}/availability",
        params={"check_in_date": "2026-03-12", "check_out_date": "2026-03-13"},
    )
    assert availability_checkout_day.status_code == 200
    assert availability_checkout_day.json()["available"] is True

    register_customer_2 = client.post(
        "/api/auth/register",
        json={
            "username": "customer_two",
            "password": "customer123",
            "full_name": "Jerry",
            "phone": "13000000002",
        },
    )
    assert register_customer_2.status_code == 201
    customer_2_id = register_customer_2.json()["id"]

    overlap_booking = client.post(
        "/api/bookings",
        headers={"X-User-Id": str(customer_2_id)},
        json={
            "property_id": property_id,
            "check_in_date": "2026-03-11",
            "check_out_date": "2026-03-13",
            "guest_count": 2,
            "guest_name": "Jerry",
            "guest_phone": "13000000002",
            "note": "测试冲突",
        },
    )
    assert overlap_booking.status_code == 409

    checkout_day_booking = client.post(
        "/api/bookings",
        headers={"X-User-Id": str(customer_2_id)},
        json={
            "property_id": property_id,
            "check_in_date": "2026-03-12",
            "check_out_date": "2026-03-13",
            "guest_count": 2,
            "guest_name": "Jerry",
            "guest_phone": "13000000002",
            "note": "退房当日中午后可接新客",
        },
    )
    assert checkout_day_booking.status_code == 201
    assert checkout_day_booking.json()["total_nights"] == 1
