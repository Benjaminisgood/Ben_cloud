from __future__ import annotations


def test_home_page_contains_business_sections(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.text
    assert "精选房源" in body
    assert "管理员入口" in body
    assert "便捷预订" in body
