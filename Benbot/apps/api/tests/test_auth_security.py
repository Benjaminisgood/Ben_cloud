from __future__ import annotations

from benbot_api.services.web_pages import sanitize_next_url


def test_sanitize_next_url_allows_local_path() -> None:
    assert sanitize_next_url("/dashboard?tab=overview") == "/dashboard?tab=overview"


def test_sanitize_next_url_blocks_external_urls() -> None:
    assert sanitize_next_url("https://evil.example/steal") == "/"


def test_sanitize_next_url_blocks_protocol_relative_urls() -> None:
    assert sanitize_next_url("//evil.example/steal") == "/"


def test_sanitize_next_url_blocks_plain_relative_urls() -> None:
    assert sanitize_next_url("dashboard") == "/"
