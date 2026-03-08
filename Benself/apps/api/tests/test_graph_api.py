from __future__ import annotations


def _login(client):
    response = client.post(
        "/login",
        data={"username": "benbenbuben", "password": "benbenbuben", "next": "/"},
        follow_redirects=False,
    )
    assert response.status_code == 303


def test_agent_context_api_returns_compiled_snapshot(client):
    _login(client)

    response = client.get("/api/agent-context")

    assert response.status_code == 200
    payload = response.json()
    assert "prompt_block" in payload
    assert payload["confirmed_facts"]


def test_graph_sync_preview_roundtrip(client):
    _login(client)

    created = client.post("/api/graph-sync-runs", json={"mode": "preview"})
    assert created.status_code == 201
    payload = created.json()
    assert payload["status"] == "preview"
    assert payload["raw_episode_count"] >= 1

    listed = client.get("/api/graph-sync-runs")
    assert listed.status_code == 200
    assert listed.json()[0]["mode"] == "preview"


def test_graph_search_returns_503_when_graphiti_is_unavailable(client):
    _login(client)

    response = client.get("/api/graph-search", params={"q": "健康"})

    assert response.status_code == 503
    assert "Graphiti" in response.json()["detail"] or "OPENAI_API_KEY" in response.json()["detail"]
