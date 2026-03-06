from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Content, Record, Tag, User
from benoss_api.services import notice_views


@pytest.fixture(autouse=True)
def _stub_digest_timezone(monkeypatch) -> None:
    monkeypatch.setattr(notice_views, "get_setting_str", lambda *_args, **_kwargs: "Asia/Shanghai")
    notice_views._notice_timezone.cache_clear()
    yield
    notice_views._notice_timezone.cache_clear()


def _record(record_id: int, *, kind: str = "text") -> Record:
    user = User(id=1, username="alice", role="user", is_active=True)
    content = Content(
        id=record_id,
        kind=kind,
        text_content="fallback",
        oss_key="oss://test",
        filename="a.txt",
        file_type="file",
        content_type="text/plain",
        size_bytes=12,
    )
    record = Record(id=record_id, user_id=1, content_id=record_id, visibility="public", preview="hello")
    record.user = user
    record.content = content
    record.created_at = datetime(2026, 1, 2, 3, 4, 5)
    record.tags = [Tag(name="FastAPI", name_norm="fastapi")]
    return record


def test_parse_user_id_filter() -> None:
    assert notice_views.parse_user_id_filter("12") == 12
    assert notice_views.parse_user_id_filter("abc") is None
    assert notice_views.parse_user_id_filter("") is None


def test_parse_day_filter() -> None:
    start, end = notice_views.parse_day_filter("2026-01-02")
    assert start is not None and end is not None
    assert (end - start).days == 1


def test_parse_day_filter_invalid() -> None:
    with pytest.raises(ValueError):
        notice_views.parse_day_filter("2026-99-99")


def test_content_payload_text_fallback(monkeypatch) -> None:
    monkeypatch.setattr(notice_views, "_get_oss_text", lambda *_: (_ for _ in ()).throw(RuntimeError("x")))
    content = Content(id=1, kind="text", text_content="fallback-text", oss_key="x", size_bytes=3)
    payload = notice_views.content_payload(content, text_source="oss")
    assert payload is not None
    assert payload["text"] == "fallback-text"


def test_records_response_has_more() -> None:
    rows = [_record(3), _record(2), _record(1)]
    out = notice_views.records_response(rows, limit=2, text_source="db")
    assert out["has_more"] is True
    assert len(out["items"]) == 2


def test_render_notice_html_contains_article() -> None:
    html = notice_views.render_notice_html([_record(1)])
    assert "notice-reader-layout" in html
    assert "notice-context-rail" in html
    assert "notice-record-1" in html
    assert 'data-notice-anchor="#notice-record-1"' in html
    assert "#FastAPI" in html
    assert "notice-text-content" in html
    assert "notice-block-head" not in html
    assert "notice-preview" not in html
    assert "notice-meta-tags" not in html


def test_render_notice_html_escapes_preview_html() -> None:
    row = _record(1)
    row.preview = "<script>alert('x')</script>"
    html = notice_views.render_notice_html([row])
    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;" in html


def test_render_notice_html_empty_state() -> None:
    html = notice_views.render_notice_html([])
    assert "暂无匹配记录" in html
    assert "notice-context-rail" in html


def test_render_notice_html_shows_edit_action_for_owner() -> None:
    html = notice_views.render_notice_html([_record(1)], viewer_user_id=1)
    assert 'data-action="edit-record"' in html
    assert 'data-record-id="1"' in html


def test_render_notice_html_hides_edit_action_for_non_owner() -> None:
    html = notice_views.render_notice_html([_record(1)], viewer_user_id=2)
    assert 'data-action="edit-record"' not in html


def test_render_notice_html_uses_digest_timezone_for_context_time() -> None:
    row = _record(1)
    row.created_at = datetime(2026, 1, 2, 18, 4, 5)
    html = notice_views.render_notice_html([row])
    assert 'data-day="2026-01-03"' in html
    assert ">02:04<" in html
