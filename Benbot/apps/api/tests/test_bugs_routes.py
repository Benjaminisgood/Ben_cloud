from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from benbot_api.api.routes import bugs


def test_get_archived_bugs_returns_service_response(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bugs,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        bugs.bug_service,
        "list_archived",
        lambda _db: [{"id": 5, "reporter": "alice", "body": "done", "status": "archived", "created_at": "", "approved_at": ""}],
    )

    result = bugs.get_archived_bugs(request=object(), db=object())

    assert result[0]["status"] == "archived"
    assert result[0]["id"] == 5


def test_clear_archived_bugs_returns_deleted_count(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bugs,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        bugs.bug_service,
        "clear_archived",
        lambda _db: 6,
    )

    result = bugs.clear_archived_bugs(request=object(), db=object())

    assert result == {"ok": True, "cleared_count": 6}


def test_archive_bug_returns_archived_bug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bugs,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        bugs.bug_service,
        "archive_bug",
        lambda _db, bug_id: {
            "id": bug_id,
            "reporter": "alice",
            "body": "done",
            "status": "archived",
            "created_at": "2026-03-07 10:00",
            "approved_at": "2026-03-07 11:00",
        },
    )

    result = bugs.archive_bug(bug_id=12, request=object(), db=object())

    assert result["ok"] is True
    assert result["bug"]["id"] == 12
    assert result["bug"]["status"] == "archived"


def test_archive_bug_translates_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bugs,
        "require_admin_session_user_or_403",
        lambda _request, _db: SimpleNamespace(username="root", role="admin"),
    )
    monkeypatch.setattr(
        bugs.bug_service,
        "archive_bug",
        lambda _db, _bug_id: (_ for _ in ()).throw(ValueError("bug_report 7 is not approved (status=archived)")),
    )

    with pytest.raises(HTTPException) as exc_info:
        bugs.archive_bug(bug_id=7, request=object(), db=object())

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "bug_report 7 is not approved (status=archived)"
