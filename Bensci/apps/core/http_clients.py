from __future__ import annotations

from typing import Any

import requests

try:
    from openai import DefaultHttpxClient, OpenAI
except Exception:  # pragma: no cover
    DefaultHttpxClient = None  # type: ignore[assignment]
    OpenAI = None  # type: ignore[assignment]


def build_requests_session() -> requests.Session:
    session = requests.Session()
    # Avoid macOS system proxy discovery in forked gunicorn workers.
    session.trust_env = False
    return session


def request(method: str, url: str, **kwargs: Any) -> requests.Response:
    with build_requests_session() as session:
        return session.request(method=method, url=url, **kwargs)


def build_openai_client(*, api_key: str, base_url: str, timeout: float) -> OpenAI | None:
    if OpenAI is None or DefaultHttpxClient is None:
        return None
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
        timeout=timeout,
        http_client=DefaultHttpxClient(trust_env=False, timeout=timeout),
    )
