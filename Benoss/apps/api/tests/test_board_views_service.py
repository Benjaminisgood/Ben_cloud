from __future__ import annotations

import sys
from collections import namedtuple
from datetime import date
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Record
from benoss_api.services.board_views import (
    build_date_range,
    build_users_heat,
    clamp_days,
    matrix_payload,
    parse_day,
    records_list_payload,
    top_public_tags_payload,
)


def test_clamp_days_with_default_and_bounds() -> None:
    assert clamp_days(0, default_days=7) == 7
    assert clamp_days(-1, default_days=7) == 7
    assert clamp_days(999, default_days=7) == 366
    assert clamp_days(3, default_days=7) == 3


def test_parse_day_invalid() -> None:
    with pytest.raises(ValueError):
        parse_day("2026-13-40")


def test_build_date_range() -> None:
    out = build_date_range(start_date=date(2026, 1, 1), days=3)
    assert out == ["2026-01-01", "2026-01-02", "2026-01-03"]


def test_build_users_heat() -> None:
    Row = namedtuple("Row", ["user_id", "day", "cnt"])
    rows = [
        Row(user_id=2, day="2026-01-01", cnt=3),
        Row(user_id=1, day="2026-01-01", cnt=2),
        Row(user_id=1, day="2026-01-02", cnt=1),
    ]
    out = build_users_heat(
        heat_rows=rows,
        users_map={1: "alice", 2: "bob"},
        date_range=["2026-01-01", "2026-01-02"],
    )
    assert out[0]["id"] == 1
    assert out[0]["total"] == 3
    assert out[0]["counts"]["2026-01-02"] == 1


def test_matrix_payload() -> None:
    out = matrix_payload(
        [
            {"id": 8, "counts": {"2026-01-01": 2, "2026-01-02": 0}},
            {"id": 9, "counts": {"2026-01-01": 1}},
        ]
    )
    assert out == {
        "8": {"2026-01-01": 2, "2026-01-02": 0},
        "9": {"2026-01-01": 1},
    }


def test_top_public_tags_payload() -> None:
    Row = namedtuple("Row", ["name", "cnt"])
    out = top_public_tags_payload([Row(name="FastAPI", cnt=3)])
    assert out == [{"tag": "FastAPI", "count": 3}]


def test_records_list_payload_has_more() -> None:
    records = [Record(id=3, visibility="public"), Record(id=2, visibility="public"), Record(id=1, visibility="public")]
    out = records_list_payload(records, limit=2)
    assert out["has_more"] is True
    assert len(out["items"]) == 2
