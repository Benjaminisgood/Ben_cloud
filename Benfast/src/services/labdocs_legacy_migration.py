from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.labdocs_service import LabDocsService
from services.labdocs_storage import StorageBackend


def _legacy_workspace_catalog_key() -> str:
    return "workspace/catalog.json"


def _legacy_workspace_locks_key() -> str:
    return "workspace/locks.json"


def _legacy_book_key(book_id: str) -> str:
    return f"books/{book_id}/book.json"


def _legacy_page_meta_key(book_id: str, page_id: str) -> str:
    return f"books/{book_id}/pages/{page_id}.json"


def _legacy_page_body_key(book_id: str, page_id: str) -> str:
    return f"books/{book_id}/pages/{page_id}.md"


def _legacy_page_comments_key(book_id: str, page_id: str) -> str:
    return f"books/{book_id}/pages/{page_id}.comments.json"


def _legacy_page_revisions_key(book_id: str, page_id: str) -> str:
    return f"books/{book_id}/pages/{page_id}.revisions.json"


def _legacy_assets_index_key(book_id: str) -> str:
    return f"books/{book_id}/assets/index.json"


def _legacy_asset_blob_key(book_id: str, stored_name: str) -> str:
    return f"books/{book_id}/assets/files/{stored_name}"


def _legacy_publishes_key(book_id: str) -> str:
    return f"books/{book_id}/publishes.json"


def transform_legacy_catalog(legacy_catalog: dict[str, Any]) -> dict[str, Any]:
    books = legacy_catalog.get("books") or []
    pages = legacy_catalog.get("pages") or {}
    if not isinstance(books, list) or not isinstance(pages, dict):
        raise ValueError("旧版 catalog 结构无效")

    next_books: list[dict[str, Any]] = []
    next_pages: dict[str, dict[str, Any]] = {}

    for raw_book in books:
        if not isinstance(raw_book, dict):
            continue
        book = dict(raw_book)
        book_id = str(book.get("id") or "").strip()
        root_page_id = str(book.get("root_page_id") or "").strip()
        if not book_id or not root_page_id:
            continue

        related_pages = [
            dict(page)
            for page in pages.values()
            if isinstance(page, dict) and str(page.get("book_id")) == book_id
        ]
        for page in related_pages:
            page_id = str(page.get("id") or "").strip()
            if not page_id:
                continue
            if page_id == root_page_id:
                page["kind"] = "root"
                page["parent_id"] = None
                page["depth"] = 0
                page["path"] = ""
                page["slug"] = "index"
            next_pages[page_id] = page

        book["page_count"] = sum(
            1 for page in next_pages.values() if str(page.get("book_id")) == book_id
        )
        next_books.append(book)

    return {
        "books": next_books,
        "pages": next_pages,
    }


@dataclass
class LegacyMigrationStats:
    books_migrated: int
    pages_migrated: int
    assets_migrated: int
    publishes_migrated: int
    rebuilt_site: bool
    published_books: int


class LegacyLabdocsMigrator:
    def __init__(
        self,
        *,
        legacy_storage: StorageBackend,
        target_service: LabDocsService,
    ) -> None:
        self.legacy_storage = legacy_storage
        self.target_service = target_service

    def _copy_json(self, source_key: str, target_key: str, default: Any) -> Any:
        payload = self.legacy_storage.read_json(source_key, default)
        self.target_service.storage.write_json(target_key, payload)
        return payload

    def migrate(self, *, rebuild_site: bool = True) -> LegacyMigrationStats:
        legacy_catalog = self.legacy_storage.read_json(
            _legacy_workspace_catalog_key(),
            {"books": [], "pages": {}},
        )
        next_catalog = transform_legacy_catalog(legacy_catalog)
        locks = self.legacy_storage.read_json(_legacy_workspace_locks_key(), {})
        if not isinstance(locks, dict):
            locks = {}

        self.target_service.storage.write_json(
            self.target_service._catalog_key(),
            next_catalog,
        )
        self.target_service.storage.write_json(
            self.target_service._locks_key(),
            locks,
        )

        page_count = 0
        asset_count = 0
        publish_count = 0

        for book in next_catalog["books"]:
            book_id = str(book["id"])
            self.target_service.storage.write_json(
                self.target_service._book_key(book_id),
                book,
            )

            publishes = self._copy_json(
                _legacy_publishes_key(book_id),
                self.target_service._publishes_key(book_id),
                [],
            )
            if isinstance(publishes, list):
                publish_count += len(publishes)

            assets_index = self._copy_json(
                _legacy_assets_index_key(book_id),
                self.target_service._assets_key(book_id),
                [],
            )
            if isinstance(assets_index, list):
                for asset in assets_index:
                    if not isinstance(asset, dict):
                        continue
                    stored_name = str(asset.get("stored_name") or "").strip()
                    if not stored_name:
                        continue
                    payload = self.legacy_storage.read_bytes(
                        _legacy_asset_blob_key(book_id, stored_name)
                    )
                    if payload is None:
                        continue
                    self.target_service.storage.write_bytes(
                        self.target_service._asset_blob_key(book_id, stored_name),
                        payload,
                    )
                    asset_count += 1

        for page in next_catalog["pages"].values():
            book_id = str(page["book_id"])
            page_id = str(page["id"])
            self.target_service.storage.write_json(
                self.target_service._page_meta_key(book_id, page_id),
                page,
            )
            body = self.legacy_storage.read_text(_legacy_page_body_key(book_id, page_id))
            if body is not None:
                self.target_service.storage.write_text(
                    self.target_service._page_body_key(book_id, page_id),
                    body,
                )
            self._copy_json(
                _legacy_page_comments_key(book_id, page_id),
                self.target_service._page_comments_key(book_id, page_id),
                [],
            )
            self._copy_json(
                _legacy_page_revisions_key(book_id, page_id),
                self.target_service._page_revisions_key(book_id, page_id),
                [],
            )
            page_count += 1

        published_books = 0
        if rebuild_site:
            site_result = self.target_service.rebuild_site()
            published_books = int(site_result.get("published_books") or 0)

        return LegacyMigrationStats(
            books_migrated=len(next_catalog["books"]),
            pages_migrated=page_count,
            assets_migrated=asset_count,
            publishes_migrated=publish_count,
            rebuilt_site=rebuild_site,
            published_books=published_books,
        )
