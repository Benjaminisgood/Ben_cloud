from __future__ import annotations


def test_public_config_exposes_homepage_copy(client):
    response = client.get("/api/v1/public/config")

    assert response.status_code == 200

    payload = response.json()
    homepage = payload["homepage"]

    assert homepage["nav_brand"]
    assert homepage["hero_title"]
    assert homepage["capabilities_title"]
    assert homepage["workflow_summary_title"]
    assert homepage["contact_form_title"]
    assert homepage["footer_subscribe_button"]
    assert homepage["hero_image_url"].startswith("/static/")
