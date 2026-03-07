from __future__ import annotations

from pathlib import Path

from benlab_api.core.config import Settings


def test_database_url_rewrites_legacy_workspace_path() -> None:
    settings = Settings(DATABASE_URL="sqlite:////Users/ben/Desktop/Ben_cloud/Benlab/data/benlab.sqlite")
    expected = Path(__file__).resolve().parents[3] / "data" / "benlab.sqlite"
    assert settings.DATABASE_URL == f"sqlite:///{expected}"


def test_database_url_resolves_repo_relative_sqlite_path() -> None:
    settings = Settings(DATABASE_URL="sqlite:///data/benlab.sqlite")
    expected = Path(__file__).resolve().parents[3] / "data" / "benlab.sqlite"
    assert settings.DATABASE_URL == f"sqlite:///{expected}"
