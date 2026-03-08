from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from benbot_api.services import bugs


def test_list_archived_formats_rows(monkeypatch: pytest.MonkeyPatch) -> None:
    row = (
        SimpleNamespace(
            id=3,
            reporter_id=11,
            body="fixed",
            status="archived",
            created_at=datetime(2026, 3, 7, 10, 0),
            approved_at=datetime(2026, 3, 7, 12, 0),
        ),
        "alice",
    )
    monkeypatch.setattr(bugs, "list_archived_bug_reports_with_reporter", lambda _db: [row])

    result = bugs.list_archived(object())

    assert result == [{
        "id": 3,
        "reporter": "alice",
        "body": "fixed",
        "status": "archived",
        "created_at": "2026-03-07 10:00",
        "approved_at": "2026-03-07 12:00",
    }]


def test_clear_archived_returns_deleted_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bugs, "clear_archived_bug_reports", lambda _db: 4)

    result = bugs.clear_archived(object())

    assert result == 4


def test_archive_bug_marks_approved_bug_as_archived(monkeypatch: pytest.MonkeyPatch) -> None:
    bug = SimpleNamespace(
        id=8,
        reporter_id=2,
        body="archive me",
        status="approved",
        created_at=datetime(2026, 3, 7, 9, 0),
        approved_at=datetime(2026, 3, 7, 11, 0),
    )
    monkeypatch.setattr(bugs, "get_bug_report", lambda _db, _bug_id: bug)
    monkeypatch.setattr(bugs, "get_user_by_id", lambda _db, _user_id: SimpleNamespace(username="ben"))
    monkeypatch.setattr(bugs, "save_bug_report", lambda _db, value: value)

    result = bugs.archive_bug(object(), 8)

    assert bug.status == "archived"
    assert result["id"] == 8
    assert result["status"] == "archived"
    assert result["reporter"] == "ben"


def test_archive_bug_rejects_non_approved_bug(monkeypatch: pytest.MonkeyPatch) -> None:
    bug = SimpleNamespace(
        id=9,
        reporter_id=2,
        body="already archived",
        status="archived",
        created_at=datetime(2026, 3, 7, 9, 0),
        approved_at=datetime(2026, 3, 7, 11, 0),
    )
    monkeypatch.setattr(bugs, "get_bug_report", lambda _db, _bug_id: bug)

    with pytest.raises(ValueError) as exc_info:
        bugs.archive_bug(object(), 9)

    assert str(exc_info.value) == "bug_report 9 is not approved (status=archived)"
