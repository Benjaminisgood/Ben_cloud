from __future__ import annotations

from fastapi import Request

_FLASH_KEY = "_flash"


def flash(request: Request, message: str, category: str = "info") -> None:
    messages = request.session.get(_FLASH_KEY, [])
    messages.append([category, message])
    request.session[_FLASH_KEY] = messages


def pop_flash(request: Request) -> list[list[str]]:
    messages = request.session.get(_FLASH_KEY, [])
    request.session[_FLASH_KEY] = []
    return messages
