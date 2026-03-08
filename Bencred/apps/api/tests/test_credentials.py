"""Credential API tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from bencred_api.main import app


@pytest.mark.asyncio
async def test_create_credential():
    """Test creating a new credential."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/api/v1/credentials",
            json={
                "name": "Test API Key",
                "credential_type": "api_key",
                "secret_data": "sk-test123456789",
                "service_name": "OpenAI",
                "category": "ai_api",
                "tags": ["production", "chat"],
            },
        )
    
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API Key"
    assert data["credential_type"] == "api_key"
    assert data["service_name"] == "OpenAI"
    assert "id" in data
    assert data["is_active"] is True
    assert data["review_status"] == "pending"
    assert data["source"] == "agent"


@pytest.mark.asyncio
async def test_list_credentials():
    """Test listing credentials with pagination."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/credentials")
    
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


@pytest.mark.asyncio
async def test_get_credential():
    """Test getting a credential by ID."""
    # First create a credential
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/v1/credentials",
            json={
                "name": "Get Test Key",
                "credential_type": "api_key",
                "secret_data": "sk-gettest123",
                "service_name": "Test Service",
            },
        )
        credential_id = create_response.json()["id"]
        
        # Get the credential
        response = await ac.get(f"/api/v1/credentials/{credential_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test Key"
    assert "decrypted_data" not in data  # Should not include secret in normal response


@pytest.mark.asyncio
async def test_get_credential_not_found():
    """Test getting a non-existent credential."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/v1/credentials/99999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_credential():
    """Test updating a credential."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        create_response = await ac.post(
            "/api/v1/credentials",
            json={
                "name": "Update Test",
                "credential_type": "password",
                "secret_data": "oldpassword123",
            },
        )
        credential_id = create_response.json()["id"]
        
        # Update
        response = await ac.put(
            f"/api/v1/credentials/{credential_id}",
            json={"name": "Updated Name", "category": "database"},
        )
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["category"] == "database"


@pytest.mark.asyncio
async def test_review_credential():
    """Test approving a credential submission."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        create_response = await ac.post(
            "/api/v1/credentials",
            json={
                "name": "Review Test",
                "credential_type": "password",
                "secret_data": "topsecret123",
                "source": "agent",
                "source_detail": "agent://memory-sync",
            },
        )
        credential_id = create_response.json()["id"]

        review_response = await ac.post(
            f"/api/v1/credentials/{credential_id}/review",
            json={
                "review_status": "approved",
                "review_notes": "允许 agent 读取摘要",
                "reviewed_by": "Ben",
                "agent_access": "masked",
                "sensitivity": "critical",
            },
        )

    assert review_response.status_code == 200
    data = review_response.json()
    assert data["review_status"] == "approved"
    assert data["reviewed_by"] == "Ben"
    assert data["agent_access"] == "masked"
    assert data["sensitivity"] == "critical"


@pytest.mark.asyncio
async def test_delete_credential():
    """Test deleting a credential."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create
        create_response = await ac.post(
            "/api/v1/credentials",
            json={
                "name": "Delete Test",
                "credential_type": "api_key",
                "secret_data": "sk-deletetest",
            },
        )
        credential_id = create_response.json()["id"]
        
        # Delete
        response = await ac.delete(f"/api/v1/credentials/{credential_id}")
        assert response.status_code == 204
        
        # Verify deleted
        get_response = await ac.get(f"/api/v1/credentials/{credential_id}")
        assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_dashboard_page_loads():
    """Test the review dashboard page renders."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")

    assert response.status_code == 200
    assert "Bencred" in response.text
    assert "待审核" in response.text
