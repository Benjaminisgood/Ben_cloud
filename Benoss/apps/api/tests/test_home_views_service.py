from __future__ import annotations

import sys
from datetime import date, datetime
from pathlib import Path

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import GeneratedAsset, Record, Tag, User
from benoss_api.services.home_views import build_home_today_response, public_record_payload


def _record(record_id: int) -> Record:
    user = User(id=1, username="alice", role="user", is_active=True)
    record = Record(id=record_id, user_id=1, content_id=record_id, visibility="public", preview="hello")
    record.user = user
    record.created_at = datetime(2026, 1, 2, 3, 4, 5)
    record.tags = [Tag(name="FastAPI", name_norm="fastapi")]
    return record


def _asset(asset_id: int) -> GeneratedAsset:
    asset = GeneratedAsset(id=asset_id, user_id=1, kind="blog_html", visibility="public", status="ready")
    asset.created_at = datetime(2026, 1, 2, 3, 4, 5)
    asset.source_day = date(2026, 1, 1)
    return asset


def test_public_record_payload_uses_id_as_record_no() -> None:
    out = public_record_payload(_record(7))
    assert out["id"] == 7
    assert out["record_no"] == 7
    assert out["user"]["username"] == "alice"


def test_build_home_today_response() -> None:
    response = build_home_today_response(
        today=date(2026, 1, 2),
        yesterday=date(2026, 1, 1),
        timezone_name="UTC",
        public_records=[_record(2)],
        digest_assets=[_asset(3)],
        public_count=10,
        user_count=2,
        top_tags_rows=[("FastAPI", 3)],
    )
    assert response["timezone"] == "UTC"
    assert response["metrics"]["public_count"] == 10
    assert response["metrics"]["top_tags"] == ["FastAPI"]
    assert response["public_records"][0]["record_no"] == 2
    assert response["digest_assets"][0]["id"] == 3
