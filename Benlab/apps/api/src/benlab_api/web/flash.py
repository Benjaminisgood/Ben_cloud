from __future__ import annotations

from fastapi import Request

_FLASH_KEY = "_flashes"


def flash(request: Request, message: str, category: str = "info") -> None:
    existing = request.session.get(_FLASH_KEY, [])
    existing.append((category, message))
    request.session[_FLASH_KEY] = existing


def pop_flashed_messages(request: Request, with_categories: bool = False):
    raw = request.session.pop(_FLASH_KEY, [])
    if with_categories:
        return raw
    return [msg for _, msg in raw]
