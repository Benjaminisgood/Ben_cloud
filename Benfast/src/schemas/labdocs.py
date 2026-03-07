from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class BookCreateIn(BaseModel):
    title: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    summary: str = Field(default="", max_length=500)
    keywords: list[str] = Field(default_factory=list)


class BookUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    summary: str | None = Field(default=None, max_length=500)
    keywords: list[str] | None = None


class BookPageCreateIn(BaseModel):
    parent_id: str | None = None
    title: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=120)
    kind: Literal["page", "chapter"] = "page"
    order: int | None = Field(default=None, ge=0, le=100000)
    content: str = Field(default="")


class BookPageUpdateIn(BaseModel):
    expected_version: int = Field(..., ge=1)
    title: str | None = Field(default=None, min_length=1, max_length=120)
    slug: str | None = Field(default=None, min_length=1, max_length=120)
    content: str = Field(default="")
    change_note: str = Field(default="", max_length=240)


class BookPageMoveIn(BaseModel):
    parent_id: str | None = None
    order: int = Field(default=999, ge=0, le=100000)


class BookCommentIn(BaseModel):
    content: str = Field(..., min_length=1, max_length=4000)
    anchor: str | None = Field(default=None, max_length=240)


class BookLockIn(BaseModel):
    ttl_minutes: int = Field(default=15, ge=1, le=120)


class BookPublishIn(BaseModel):
    message: str = Field(default="", max_length=240)
