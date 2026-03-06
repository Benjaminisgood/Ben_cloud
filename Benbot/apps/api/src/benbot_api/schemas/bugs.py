from __future__ import annotations

from pydantic import BaseModel


class BugItem(BaseModel):
    id: int
    reporter: str
    body: str
    status: str
    created_at: str
    approved_at: str | None = None
    repaired: bool | None = None
    verified: bool | None = None


class BugSubmitResponse(BaseModel):
    ok: bool
    id: int


class BugActionResponse(BaseModel):
    ok: bool
    bug: BugItem
