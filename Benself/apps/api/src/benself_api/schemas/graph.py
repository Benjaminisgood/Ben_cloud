from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class GraphSyncRunCreate(BaseModel):
    mode: Literal["preview", "sync"] = "preview"


class GraphSyncRunRead(BaseModel):
    id: int
    mode: str
    status: str
    raw_episode_count: int
    confirmed_episode_count: int
    backend: str
    message: str
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}


class GraphSearchResult(BaseModel):
    name: str
    fact: str
    valid_at: str | None = None
    invalid_at: str | None = None
    episodes: list[str]


class GraphSearchResponse(BaseModel):
    query: str
    results: list[GraphSearchResult]
