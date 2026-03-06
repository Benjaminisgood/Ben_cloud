from __future__ import annotations


def test_customer_cannot_create_property(client):
    register_resp = client.post(
        "/api/auth/register",
        json={
            "username": "customer_a",
            "password": "customer123",
            "full_name": "Alice",
            "phone": "13000000000",
        },
    )
    assert register_resp.status_code == 201
    customer_id = register_resp.json()["id"]

    create_resp = client.post(
        "/api/admin/properties",
        headers={"X-User-Id": str(customer_id)},
        json={
            "title": "海景大床房",
            "description": "可看海",
            "city": "三亚",
            "address": "海棠湾 1 号",
            "price_per_night": 580,
            "max_guests": 2,
            "is_active": True,
        },
    )

    assert create_resp.status_code == 403
    assert create_resp.json()["detail"] == "admin only"
