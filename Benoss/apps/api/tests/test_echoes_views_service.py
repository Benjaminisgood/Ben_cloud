from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Content, GeneratedAsset, Record, Tag, User
from benoss_api.services.echoes_views import asset_file_type, build_echoes_response, content_file_type


def _viewer() -> User:
    return User(id=1, username="alice", role="user", is_active=True)


def _record(record_id: int, *, content_kind: str = "text") -> Record:
    record = Record(id=record_id, user_id=1, content_id=record_id, visibility="public", preview="hello")
    record.user = _viewer()
    record.created_at = datetime(2026, 1, 2, 3, 4, 5)
    record.tags = [Tag(name="FastAPI", name_norm="fastapi")]
    content_type = "text/plain" if content_kind == "text" else "application/octet-stream"
    filename = "a.txt" if content_kind == "text" else "a.bin"
    record.content = Content(
        id=record_id,
        kind=content_kind,
        text_content="text-content",
        filename=filename,
        content_type=content_type,
        size_bytes=12,
    )
    return record


def _asset(asset_id: int, *, kind: str = "blog_html") -> GeneratedAsset:
    asset = GeneratedAsset(id=asset_id, user_id=1, kind=kind, visibility="public", status="ready")
    asset.content_type = "text/html"
    asset.ext = ".html"
    asset.created_at = datetime(2026, 1, 2, 3, 4, 5)
    return asset


def test_content_file_type_text() -> None:
    assert content_file_type(_record(1, content_kind="text")) == "text"


def test_asset_file_type_blog_html() -> None:
    assert asset_file_type(_asset(1, kind="blog_html")) == "web"


def test_build_echoes_response_with_filter() -> None:
    response = build_echoes_response(
        records=[_record(2, content_kind="text"), _record(1, content_kind="file")],
        assets=[_asset(3, kind="blog_html"), _asset(2, kind="podcast")],
        viewer=_viewer(),
        file_type="text",
        scope="with_mine",
        limit=10,
    )
    assert len(response["records"]) == 1
    assert response["records"][0]["file_type"] == "text"
    assert len(response["entries"]) == 1
    assert response["entries"][0]["entry_type"] == "record"
    assert response["scope"] == "with_mine"


def test_build_echoes_response_next_cursor() -> None:
    response = build_echoes_response(
        records=[_record(3), _record(2), _record(1)],
        assets=[],
        viewer=_viewer(),
        file_type="",
        scope="with_mine",
        limit=2,
    )
    assert len(response["entries"]) == 2
    assert response["has_more"] is True
    assert response["next_cursor"]["entry_type"] == "record"
    assert response["next_cursor"]["id"] == 2
