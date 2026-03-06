from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class VectorServiceError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _optional_int(value: object, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise VectorServiceError(f"{field_name} must be an integer", status_code=400) from exc


def build_chat_response(body: Mapping[str, Any]) -> dict:
    query = str(body.get("query") or "").strip()
    if not query:
        raise VectorServiceError("query is required", status_code=400)
    top_k = _optional_int(body.get("top_k"), field_name="top_k")

    try:
        from ..utils.local_vector_db import ensure_index, search as vector_search

        ensure_index()
        results = vector_search(query, top_k=top_k)
    except VectorServiceError:
        raise
    except Exception as exc:
        raise VectorServiceError(str(exc), status_code=500) from exc
    return {"results": results, "query": query}


def build_rebuild_response(body: Mapping[str, Any]) -> dict:
    force = bool(body.get("force"))
    max_docs = _optional_int(body.get("max_docs"), field_name="max_docs")
    try:
        from ..utils.local_vector_db import build_index

        return build_index(max_docs=max_docs, force=force)
    except VectorServiceError:
        raise
    except Exception as exc:
        raise VectorServiceError(str(exc), status_code=500) from exc


def build_meta_response() -> dict:
    try:
        from ..utils.local_vector_db import index_meta

        return index_meta()
    except VectorServiceError:
        raise
    except Exception as exc:
        raise VectorServiceError(str(exc), status_code=500) from exc
