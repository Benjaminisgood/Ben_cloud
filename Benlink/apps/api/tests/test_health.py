"""Health check tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from benlink_api.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Test health check endpoint returns healthy status."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]
    assert data["app"] == "Benlink"
    assert "version" in data
    assert "database" in data
