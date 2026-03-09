from __future__ import annotations

import time

from apps.core.config import settings
from apps.core.http_clients import request


class HttpProviderMixin:
    timeout_seconds = settings.request_timeout_seconds

    def _session_headers(self) -> dict[str, str]:
        return {"User-Agent": settings.request_user_agent}

    def _get(self, url: str, *, params: dict | None = None, headers: dict | None = None):
        merged_headers = self._session_headers()
        if headers:
            merged_headers.update(headers)
        response = request("GET", url, params=params, headers=merged_headers, timeout=self.timeout_seconds)
        return response

    def _sleep(self) -> None:
        if settings.provider_sleep_seconds > 0:
            time.sleep(settings.provider_sleep_seconds)
