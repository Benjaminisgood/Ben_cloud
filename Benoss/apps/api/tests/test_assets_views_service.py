from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import DailyDigestJob, GeneratedAsset
from benoss_api.services.assets_views import asset_payload, asset_visible, parse_day, parse_source_day


def _asset(asset_id: int, *, kind: str = "blog_html", visibility: str = "public", user_id: int = 1) -> GeneratedAsset:
    asset = GeneratedAsset(id=asset_id, user_id=user_id, kind=kind, visibility=visibility, status="ready")
    asset.content_type = "text/html"
    asset.ext = ".html"
    asset.created_at = datetime(2026, 1, 2, 3, 4, 5)
    asset.source_day = date(2026, 1, 1)
    return asset


def test_parse_source_day() -> None:
    assert parse_source_day("2026-01-02") == date(2026, 1, 2)
    assert parse_source_day("bad") is None
    assert parse_source_day("") is None


def test_parse_day_invalid() -> None:
    with pytest.raises(ValueError):
        parse_day("2026-99-99")


def test_asset_visible() -> None:
    public_asset = _asset(1, visibility="public", user_id=2)
    private_asset = _asset(2, visibility="private", user_id=2)
    assert asset_visible(public_asset, viewer_user_id=1)
    assert not asset_visible(private_asset, viewer_user_id=1)
    assert asset_visible(private_asset, viewer_user_id=2)


def test_asset_payload_blog_html_is_web() -> None:
    out = asset_payload(_asset(3, kind="blog_html"))
    assert out["file_type"] == "web"
    assert out["blob_url"].endswith("/3/blob")


def test_job_payload_nested_assets() -> None:
    from benoss_api.services.assets_views import job_payload

    blog = _asset(10)
    job = DailyDigestJob(day=date(2026, 1, 1), timezone="UTC", status="ready")
    job.blog_asset_id = 10
    job.blog_asset = blog
    payload = job_payload(job)
    assert payload["day"] == "2026-01-01"
    assert payload["blog_asset"]["id"] == 10
