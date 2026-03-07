from __future__ import annotations

from pathlib import Path

from settings.config import Settings


def test_sqlite_and_docs_paths_rewrite_legacy_workspace_paths() -> None:
    settings = Settings(
        DB_ENGINE="sqlite",
        SQLITE_DB_PATH="/Users/ben/Desktop/Ben_cloud/Benfast/data/benfast.sqlite3",
        DOCS_SITE_DIR="/Users/ben/Desktop/Ben_cloud/Benfast/site",
        LABDOCS_LOCAL_ROOT="/Users/ben/Desktop/Ben_cloud/Benfast/data/labbooks",
        LABDOCS_DOCS_SOURCE_ROOT="/Users/ben/Desktop/Ben_cloud/Benfast/data/docs_site_source",
        LABDOCS_PUBLISH_ROOT="/Users/ben/Desktop/Ben_cloud/Benfast/site/books",
        SWAGGER_UI_PASSWORD="test-password",
    )
    repo_root = Path(__file__).resolve().parents[1]
    assert settings.SQLITE_DB_PATH == str(repo_root / "data" / "benfast.sqlite3")
    assert settings.DOCS_SITE_DIR == str(repo_root / "site")
    assert settings.LABDOCS_LOCAL_ROOT == str(repo_root / "data" / "labbooks")
    assert settings.LABDOCS_DOCS_SOURCE_ROOT == str(repo_root / "data" / "docs_site_source")
    assert settings.LABDOCS_PUBLISH_ROOT == str(repo_root / "site" / "books")


def test_sqlite_and_docs_paths_resolve_repo_relative_values() -> None:
    settings = Settings(
        DB_ENGINE="sqlite",
        SQLITE_DB_PATH="data/benfast.sqlite3",
        DOCS_SITE_DIR="site",
        LABDOCS_LOCAL_ROOT="data/labbooks",
        LABDOCS_DOCS_SOURCE_ROOT="data/docs_site_source",
        LABDOCS_PUBLISH_ROOT="site/books",
        SWAGGER_UI_PASSWORD="test-password",
    )
    repo_root = Path(__file__).resolve().parents[1]
    assert settings.SQLITE_DB_PATH == str(repo_root / "data" / "benfast.sqlite3")
    assert settings.DOCS_SITE_DIR == str(repo_root / "site")
    assert settings.LABDOCS_LOCAL_ROOT == str(repo_root / "data" / "labbooks")
    assert settings.LABDOCS_DOCS_SOURCE_ROOT == str(repo_root / "data" / "docs_site_source")
    assert settings.LABDOCS_PUBLISH_ROOT == str(repo_root / "site" / "books")
