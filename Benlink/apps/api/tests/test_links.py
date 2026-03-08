"""Link API tests."""
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from benlink_api.main import app


def _unique_url() -> str:
    return f"https://example.com/{uuid.uuid4().hex}"


@pytest.mark.asyncio
async def test_create_link():
    """Test creating a new link without fetching metadata."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/links?fetch_metadata=false",
            json={
                "url": _unique_url(),
                "category": "reference",
                "tags": ["ai", "docs"],
                "source": "agent",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["review_status"] == "pending"
    assert data["source"] == "agent"
    assert data["category"] == "reference"


@pytest.mark.asyncio
async def test_list_links():
    """Test listing links with pagination."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/links")

    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_review_link():
    """Test approving a link submission."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/v1/links?fetch_metadata=false",
            json={
                "url": _unique_url(),
                "notes": "worth reading later",
            },
        )
        link_id = create_response.json()["id"]

        review_response = await ac.post(
            f"/api/v1/links/{link_id}/review",
            json={
                "review_status": "approved",
                "review_notes": "沉淀到正式资料库",
                "reviewed_by": "Ben",
                "category": "reading",
                "priority": "high",
                "is_favorite": True,
            },
        )

    assert review_response.status_code == 200
    data = review_response.json()
    assert data["review_status"] == "approved"
    assert data["reviewed_by"] == "Ben"
    assert data["category"] == "reading"
    assert data["priority"] == "high"
    assert data["is_favorite"] is True


@pytest.mark.asyncio
async def test_dashboard_page_loads():
    """Test the review dashboard page renders."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    assert "Benlink" in response.text
    assert "待审核" in response.text
