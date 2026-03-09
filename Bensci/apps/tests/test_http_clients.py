from __future__ import annotations

from apps.core.http_clients import build_openai_client, build_requests_session


def test_requests_session_disables_env_proxy_lookup() -> None:
    with build_requests_session() as session:
        assert session.trust_env is False


def test_openai_client_disables_env_proxy_lookup() -> None:
    client = build_openai_client(
        api_key="test-key",
        base_url="https://example.com/v1",
        timeout=3.0,
    )
    assert client is not None
    try:
        assert getattr(client._client, "_trust_env", None) is False
    finally:
        client.close()
