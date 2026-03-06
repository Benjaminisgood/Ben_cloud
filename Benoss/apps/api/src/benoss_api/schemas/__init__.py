from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class UserOut(BaseModel):
    id: int
    username: str
    description: str = ""

    class Config:
        from_attributes = True


class ContentOut(BaseModel):
    id: int
    kind: str
    file_type: str
    text: str | None = None
    filename: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    sha256: str | None = None
    media_type: str | None = None
    blob_url: str | None = None
    signed_url: str | None = None

    class Config:
        from_attributes = True


class RecordOut(BaseModel):
    id: int
    record_no: int
    visibility: str
    tags: list[str]
    preview: str
    created_at: str
    updated_at: str
    can_edit: bool
    can_comment: bool
    user: UserOut
    content: ContentOut | None = None

    class Config:
        from_attributes = True


class CommentOut(BaseModel):
    id: int
    body: str
    created_at: str
    user: UserOut

    class Config:
        from_attributes = True


class GeneratedAssetOut(BaseModel):
    id: int
    kind: str
    title: str
    provider: str
    model: str
    visibility: str
    status: str
    is_daily_digest: bool
    source_day: str | None
    file_type: str
    size_bytes: int
    oss_key: str
    created_at: str

    class Config:
        from_attributes = True


class TagOut(BaseModel):
    name: str
    count: int


class Paginated(BaseModel):
    items: list[Any]
    total: int | None = None
    has_more: bool = False
