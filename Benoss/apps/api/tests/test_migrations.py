from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

import pytest

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.db import migrations


def _mock_revision_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(migrations, "_collect_revision_graph", lambda: ({"rev_head"}, {"rev_head"}))


def _noop_lock(monkeypatch: pytest.MonkeyPatch) -> None:
    @contextmanager
    def _lock():
        yield

    monkeypatch.setattr(migrations, "_migration_lock", _lock)


def test_ensure_migration_state_auto_upgrade_when_schema_uninitialized(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_revision_graph(monkeypatch)
    _noop_lock(monkeypatch)

    state = {"validate_calls": 0, "upgrade_calls": 0}

    def _fake_validate(_: set[str], __: set[str]) -> None:
        state["validate_calls"] += 1
        if state["validate_calls"] <= 2:
            raise migrations.MigrationStateError("schema_not_initialized", "db missing")

    def _fake_upgrade() -> None:
        state["upgrade_calls"] += 1

    monkeypatch.setattr(migrations, "_validate_migration_state", _fake_validate)
    monkeypatch.setattr(migrations, "_upgrade_to_head", _fake_upgrade)

    migrations.ensure_migration_state(auto_upgrade=True)

    assert state["upgrade_calls"] == 1
    assert state["validate_calls"] == 3


def test_ensure_migration_state_auto_upgrade_skips_unknown_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_revision_graph(monkeypatch)
    _noop_lock(monkeypatch)

    state = {"upgrade_calls": 0}

    def _fake_validate(_: set[str], __: set[str]) -> None:
        raise migrations.MigrationStateError("unknown_revision", "unknown revision")

    def _fake_upgrade() -> None:
        state["upgrade_calls"] += 1

    monkeypatch.setattr(migrations, "_validate_migration_state", _fake_validate)
    monkeypatch.setattr(migrations, "_upgrade_to_head", _fake_upgrade)

    with pytest.raises(RuntimeError, match="unknown revision"):
        migrations.ensure_migration_state(auto_upgrade=True)

    assert state["upgrade_calls"] == 0


def test_ensure_migration_state_without_auto_upgrade_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_revision_graph(monkeypatch)

    def _fake_validate(_: set[str], __: set[str]) -> None:
        raise migrations.MigrationStateError("not_at_head", "not at head")

    monkeypatch.setattr(migrations, "_validate_migration_state", _fake_validate)

    with pytest.raises(RuntimeError, match="not at head"):
        migrations.ensure_migration_state(auto_upgrade=False)
