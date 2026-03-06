from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import DailyDigestJob, GeneratedAsset
from benoss_api.services.digest_views import (
    digest_refresh_response,
    parse_digest_request,
    refresh_job_from_assets,
    resolve_digest_day,
)


def _asset(asset_id: int, kind: str) -> GeneratedAsset:
    return GeneratedAsset(id=asset_id, user_id=1, kind=kind, visibility="public", status="ready")


def test_parse_digest_request() -> None:
    tz, day, force = parse_digest_request({"timezone": "UTC", "day": "2026-01-02", "force": 1}, default_timezone="Asia/Shanghai")
    assert tz == "UTC"
    assert day == "2026-01-02"
    assert force is True


def test_resolve_digest_day_invalid() -> None:
    with pytest.raises(ValueError):
        resolve_digest_day("2026-99-99", "UTC")


def test_refresh_job_from_assets_ready() -> None:
    job = DailyDigestJob(day=date(2026, 1, 2), timezone="UTC")
    assets = [_asset(1, "blog_html"), _asset(2, "podcast_audio")]
    refresh_job_from_assets(job, assets)
    assert job.status == "ready"
    assert job.blog_asset_id == 1
    assert job.podcast_asset_id == 2


def test_digest_refresh_response() -> None:
    payload = digest_refresh_response(
        day_value=date(2026, 1, 2),
        timezone_name="UTC",
        force=False,
        assets=[_asset(3, "poster_image")],
        error="",
    )
    assert payload["day"] == "2026-01-02"
    assert payload["status"] == "ready"
    assert payload["assets"][0]["id"] == 3
