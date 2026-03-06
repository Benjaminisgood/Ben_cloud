from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from benbot_api.services import bug_repair


def test_log_repair_complete_updates_matching_entry_only(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repair_log = tmp_path / "repair_log.md"
    monkeypatch.setattr(bug_repair, "_REPAIR_LOG_PATH", repair_log)

    op_1 = bug_repair.log_repair_start("bug-a", ["a.py"])
    op_2 = bug_repair.log_repair_start("bug-b", ["b.py"])

    completed_op = bug_repair.log_repair_complete("bug-b", ["fixed b"], "/tmp/backup.zip")
    content = repair_log.read_text(encoding="utf-8")

    assert completed_op == op_2
    assert "bug-a" in content
    assert "bug-b" in content
    assert content.count("status: completed") == 1
    assert content.count("status: in_progress") == 1
    assert "fixed b" in content
    assert op_1 in content


def test_get_unrepaired_bugs_filters_repaired_items(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    items = [
        SimpleNamespace(id=1, body="bug-1", approved_at=None, repaired=0),
        SimpleNamespace(id=2, body="bug-2", approved_at=None, repaired=1),
        SimpleNamespace(id=3, body="bug-3", approved_at=None, repaired=0),
    ]
    monkeypatch.setattr(bug_repair, "list_approved_bug_reports", lambda _db: items)

    result = bug_repair.get_unrepaired_bugs(db=object())
    assert [item["id"] for item in result] == [1, 3]
