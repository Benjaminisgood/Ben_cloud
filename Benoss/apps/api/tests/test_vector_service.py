from __future__ import annotations

import sys
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.services.vector_service import (
    VectorServiceError,
    build_chat_response,
    build_meta_response,
    build_rebuild_response,
)


def test_build_chat_response_requires_query() -> None:
    with pytest.raises(VectorServiceError) as exc:
        build_chat_response({})
    assert exc.value.status_code == 400
    assert exc.value.detail == "query is required"


def test_build_chat_response_invalid_top_k() -> None:
    with pytest.raises(VectorServiceError) as exc:
        build_chat_response({"query": "hello", "top_k": "bad"})
    assert exc.value.status_code == 400
    assert "top_k" in exc.value.detail


def test_build_chat_response_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from benoss_api.utils import local_vector_db

    called = {"ensure": 0}
    monkeypatch.setattr(local_vector_db, "ensure_index", lambda: called.__setitem__("ensure", 1))
    monkeypatch.setattr(local_vector_db, "search", lambda query, top_k=None: [{"query": query, "top_k": top_k}])

    out = build_chat_response({"query": "hello", "top_k": "3"})
    assert called["ensure"] == 1
    assert out["query"] == "hello"
    assert out["results"][0]["top_k"] == 3


def test_build_rebuild_response_invalid_max_docs() -> None:
    with pytest.raises(VectorServiceError) as exc:
        build_rebuild_response({"max_docs": "bad"})
    assert exc.value.status_code == 400
    assert "max_docs" in exc.value.detail


def test_build_rebuild_response_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from benoss_api.utils import local_vector_db

    monkeypatch.setattr(local_vector_db, "build_index", lambda max_docs=None, force=False: {"max_docs": max_docs, "force": force})
    out = build_rebuild_response({"max_docs": "9", "force": True})
    assert out == {"max_docs": 9, "force": True}


def test_build_meta_response_success(monkeypatch: pytest.MonkeyPatch) -> None:
    from benoss_api.utils import local_vector_db

    monkeypatch.setattr(local_vector_db, "index_meta", lambda: {"docs": 12})
    assert build_meta_response() == {"docs": 12}
