from __future__ import annotations

from fastapi.testclient import TestClient

from apps.main import app


def test_legacy_metadata_endpoint_returns_ok() -> None:
    with TestClient(app) as client:
        response = client.get("/api/metadata")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["health"] == "/api/health"
