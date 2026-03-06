from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from benbot_api.api.routes import bug_repair


class _User:
    role = "admin"
    username = "admin"


def _request() -> SimpleNamespace:
    return SimpleNamespace(client=SimpleNamespace(host="127.0.0.1"))


def test_prepare_repair_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bug_repair,
        "require_admin_principal_or_401",
        lambda _request, _db, required_scope=None: _User(),
    )
    monkeypatch.setattr(
        bug_repair.bug_repair,
        "require_approved_bug_for_repair",
        lambda _db, _bug_id: SimpleNamespace(id=11, body="test bug", status="approved"),
    )
    monkeypatch.setattr(bug_repair, "backup_project_files", lambda _bug_body: ("/tmp/backup.zip", ["a.py"]))
    monkeypatch.setattr(bug_repair.bug_repair, "log_repair_start", lambda _bug_body, _files: "op-1")

    result = bug_repair.prepare_repair(11, request=_request(), db=object())
    assert result["ok"] is True
    assert result["bug_id"] == 11
    assert result["repair_log_operation_id"] == "op-1"
    assert result["backed_up_files"] == ["a.py"]


def test_prepare_repair_returns_404_for_missing_bug(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bug_repair,
        "require_admin_principal_or_401",
        lambda _request, _db, required_scope=None: _User(),
    )

    def _missing_bug(_db, _bug_id):
        raise ValueError("Bug not found")

    monkeypatch.setattr(bug_repair.bug_repair, "require_approved_bug_for_repair", _missing_bug)

    with pytest.raises(HTTPException) as exc_info:
        bug_repair.prepare_repair(999, request=_request(), db=object())
    assert exc_info.value.status_code == 404


def test_complete_repair_marks_bug_repaired(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        bug_repair,
        "require_admin_principal_or_401",
        lambda _request, _db, required_scope=None: _User(),
    )
    source_bug = SimpleNamespace(id=12, body="repair me", repaired=0, status="approved")
    monkeypatch.setattr(
        bug_repair.bug_repair,
        "require_approved_bug_for_repair",
        lambda _db, _bug_id: source_bug,
    )
    monkeypatch.setattr(
        bug_repair.bug_repair,
        "log_repair_complete",
        lambda _bug_body, _changes, _backup: "op-2",
    )
    monkeypatch.setattr(
        bug_repair.bug_repair,
        "mark_bug_repaired",
        lambda _db, bug: SimpleNamespace(id=bug.id, body=bug.body, repaired=1),
    )

    result = bug_repair.complete_repair(
        12,
        request=_request(),
        changes=["fix-1"],
        backup_location="/tmp/backup.zip",
        db=object(),
    )
    assert result["ok"] is True
    assert result["bug_id"] == 12
    assert result["repair_log_operation_id"] == "op-2"
    assert result["repaired"] is True
