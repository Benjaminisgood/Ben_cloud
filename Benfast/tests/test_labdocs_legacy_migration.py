from pathlib import Path

from services.labdocs_legacy_migration import (
    LegacyLabdocsMigrator,
    transform_legacy_catalog,
)
from services.labdocs_service import LabDocsService
from services.labdocs_storage import LocalStorageBackend


def test_transform_legacy_catalog_converts_root_kind() -> None:
    legacy = {
        "books": [
            {
                "id": "doc-1",
                "title": "Handbook",
                "slug": "handbook",
                "root_page_id": "page-root",
                "page_count": 1,
            }
        ],
        "pages": {
            "page-root": {
                "id": "page-root",
                "book_id": "doc-1",
                "kind": "page",
                "parent_id": None,
                "depth": 0,
                "path": "",
                "slug": "index",
                "title": "Handbook",
            }
        },
    }

    migrated = transform_legacy_catalog(legacy)

    assert migrated["books"][0]["page_count"] == 1
    assert migrated["pages"]["page-root"]["kind"] == "root"
    assert migrated["pages"]["page-root"]["slug"] == "index"


def test_legacy_migrator_copies_workspace_into_flat_layout(tmp_path: Path) -> None:
    legacy = LocalStorageBackend(tmp_path / "legacy")
    target = LocalStorageBackend(tmp_path / "target")
    service = LabDocsService(storage=target, publish_root=tmp_path / "publish")
    migrator = LegacyLabdocsMigrator(legacy_storage=legacy, target_service=service)

    legacy.write_json(
        "workspace/catalog.json",
        {
            "books": [
                {
                    "id": "doc-1",
                    "title": "Handbook",
                    "slug": "handbook",
                    "root_page_id": "root-1",
                    "page_count": 2,
                    "published_url": "/kb/books/handbook/",
                    "last_publish_at": "2026-03-07T04:02:01.977219+00:00",
                }
            ],
            "pages": {
                "root-1": {
                    "id": "root-1",
                    "book_id": "doc-1",
                    "kind": "page",
                    "parent_id": None,
                    "depth": 0,
                    "path": "",
                    "slug": "index",
                    "title": "Handbook",
                },
                "page-2": {
                    "id": "page-2",
                    "book_id": "doc-1",
                    "kind": "page",
                    "parent_id": "root-1",
                    "depth": 1,
                    "path": "intro",
                    "slug": "intro",
                    "title": "Intro",
                },
            },
        },
    )
    legacy.write_json("workspace/locks.json", {"page-2": {"holder": "tester"}})
    legacy.write_text("books/doc-1/pages/root-1.md", "# Handbook")
    legacy.write_text("books/doc-1/pages/page-2.md", "# Intro")
    legacy.write_json("books/doc-1/pages/page-2.comments.json", [{"id": "comment-1"}])
    legacy.write_json("books/doc-1/pages/page-2.revisions.json", [{"id": "rev-1"}])
    legacy.write_json("books/doc-1/assets/index.json", [{"stored_name": "figure.png"}])
    legacy.write_bytes("books/doc-1/assets/files/figure.png", b"png")
    legacy.write_json("books/doc-1/publishes.json", [{"id": "pub-1"}])

    stats = migrator.migrate(rebuild_site=False)

    assert stats.books_migrated == 1
    assert stats.pages_migrated == 2
    assert stats.assets_migrated == 1
    assert stats.publishes_migrated == 1
    assert target.read_json("catalog.json", {})["pages"]["root-1"]["kind"] == "root"
    assert target.read_text("doc-1/pages/page-2.md") == "# Intro"
    assert target.read_json("doc-1/pages/page-2.comments.json", []) == [{"id": "comment-1"}]
    assert target.read_json("doc-1/publishes.json", []) == [{"id": "pub-1"}]
    assert target.read_bytes("doc-1/assets/files/figure.png") == b"png"
