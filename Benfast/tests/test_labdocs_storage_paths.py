from pathlib import Path

from services.labdocs_service import LabDocsService
from services.labdocs_storage import LocalStorageBackend


def test_labdocs_storage_keys_use_flat_document_layout(tmp_path: Path) -> None:
    service = LabDocsService(
        storage=LocalStorageBackend(tmp_path / "storage"),
        publish_root=tmp_path / "publish",
    )

    assert service._catalog_key() == "catalog.json"
    assert service._locks_key() == "locks.json"
    assert service._book_key("doc-123") == "doc-123/document.json"
    assert service._page_meta_key("doc-123", "page-456") == "doc-123/pages/page-456.json"
    assert service._page_body_key("doc-123", "page-456") == "doc-123/pages/page-456.md"
    assert (
        service._page_comments_key("doc-123", "page-456")
        == "doc-123/pages/page-456.comments.json"
    )
    assert (
        service._page_revisions_key("doc-123", "page-456")
        == "doc-123/pages/page-456.revisions.json"
    )
    assert service._publishes_key("doc-123") == "doc-123/publishes.json"
    assert service._assets_key("doc-123") == "doc-123/assets/index.json"
    assert (
        service._asset_blob_key("doc-123", "figure.png")
        == "doc-123/assets/files/figure.png"
    )
    assert (
        service._published_storage_key("lab-handbook", "index.html")
        == "published/lab-handbook/index.html"
    )
