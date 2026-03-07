from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
import html
import json
import mimetypes
import os
import re
import shutil
import subprocess
from pathlib import Path
from textwrap import dedent
from typing import Any
import uuid

from settings import settings
import yaml

from .labdocs_storage import StorageBackend, build_labdocs_storage


class LabDocsError(Exception):
    """Base class for collaborative book domain errors."""


class ResourceNotFoundError(LabDocsError):
    pass


class VersionConflictError(LabDocsError):
    def __init__(self, message: str, *, current_version: int):
        super().__init__(message)
        self.current_version = current_version


class LockConflictError(LabDocsError):
    def __init__(self, message: str, *, lock: dict[str, Any]):
        super().__init__(message)
        self.lock = lock


class PermissionDeniedError(LabDocsError):
    pass


class LabDocsService:
    def __init__(
        self,
        *,
        storage: StorageBackend | None = None,
        publish_root: Path | None = None,
    ) -> None:
        self.storage = storage or build_labdocs_storage()
        self.publish_root = publish_root or Path(settings.LABDOCS_PUBLISH_ROOT)
        self.publish_root.mkdir(parents=True, exist_ok=True)
        self.publish_root.parent.mkdir(parents=True, exist_ok=True)
        self.docs_source_root = Path(settings.LABDOCS_DOCS_SOURCE_ROOT)
        self.docs_source_root.mkdir(parents=True, exist_ok=True)
        self.docs_site_dir = Path(settings.DOCS_SITE_DIR)
        self.docs_site_dir.mkdir(parents=True, exist_ok=True)

    def _catalog_key(self) -> str:
        return "catalog.json"

    def _locks_key(self) -> str:
        return "locks.json"

    def _book_key(self, book_id: str) -> str:
        return f"{book_id}/document.json"

    def _page_meta_key(self, book_id: str, page_id: str) -> str:
        return f"{book_id}/pages/{page_id}.json"

    def _page_body_key(self, book_id: str, page_id: str) -> str:
        return f"{book_id}/pages/{page_id}.md"

    def _page_comments_key(self, book_id: str, page_id: str) -> str:
        return f"{book_id}/pages/{page_id}.comments.json"

    def _page_revisions_key(self, book_id: str, page_id: str) -> str:
        return f"{book_id}/pages/{page_id}.revisions.json"

    def _publishes_key(self, book_id: str) -> str:
        return f"{book_id}/publishes.json"

    def _assets_key(self, book_id: str) -> str:
        return f"{book_id}/assets/index.json"

    def _asset_blob_key(self, book_id: str, stored_name: str) -> str:
        return f"{book_id}/assets/files/{stored_name}"

    def _published_storage_key(self, book_slug: str, relative_path: str) -> str:
        cleaned = relative_path.strip().strip("/")
        return f"published/{book_slug}/{cleaned}"

    def _now_iso(self) -> str:
        return datetime.now(UTC).isoformat()

    def _display_timestamp(self, value: object) -> str:
        raw = str(value or "").strip()
        if not raw:
            return "-"
        try:
            normalized = raw.replace("Z", "+00:00")
            stamp = datetime.fromisoformat(normalized)
        except ValueError:
            return raw
        if stamp.tzinfo is not None:
            stamp = stamp.astimezone()
        return stamp.strftime("%Y-%m-%d %H:%M")

    def _load_catalog(self) -> dict[str, Any]:
        catalog = self.storage.read_json(self._catalog_key(), {})
        if not isinstance(catalog, dict):
            catalog = {}
        books = catalog.get("books")
        pages = catalog.get("pages")
        if not isinstance(books, list):
            books = []
        if not isinstance(pages, dict):
            pages = {}
        return {"books": books, "pages": pages}

    def _save_catalog(self, catalog: dict[str, Any]) -> None:
        self.storage.write_json(self._catalog_key(), catalog)

    def _load_locks(self) -> dict[str, dict[str, Any]]:
        locks = self.storage.read_json(self._locks_key(), {})
        if not isinstance(locks, dict):
            locks = {}

        now = datetime.now(UTC)
        active: dict[str, dict[str, Any]] = {}
        changed = False
        for page_id, lock in locks.items():
            if not isinstance(lock, dict):
                changed = True
                continue
            try:
                expires_at = datetime.fromisoformat(str(lock.get("expires_at", "")))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=UTC)
            except ValueError:
                changed = True
                continue
            if expires_at > now:
                active[page_id] = lock
            else:
                changed = True

        if changed:
            self.storage.write_json(self._locks_key(), active)
        return active

    def _save_locks(self, locks: dict[str, dict[str, Any]]) -> None:
        self.storage.write_json(self._locks_key(), locks)

    def _normalize_slug(self, slug: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(slug).strip().lower())
        value = re.sub(r"-+", "-", value).strip("-")
        return value or "untitled"

    def _normalize_tags(self, tags: list[str] | None) -> list[str]:
        if not tags:
            return []
        result: list[str] = []
        for raw in tags:
            item = re.sub(r"\s+", " ", str(raw).strip())
            if item and item not in result:
                result.append(item)
        return result[:20]

    def _book_keywords(self, book: dict[str, Any]) -> list[str]:
        raw = book.get("keywords")
        return self._normalize_tags(raw if isinstance(raw, list) else [])

    def _decorate_book(self, book: dict[str, Any]) -> dict[str, Any]:
        payload = dict(book)
        payload["keywords"] = self._book_keywords(payload)
        return payload

    def _normalize_asset_name(self, filename: str) -> str:
        raw = Path(str(filename or "").strip()).name or "file"
        stem = re.sub(r"[^0-9a-zA-Z\u4e00-\u9fff._-]+", "-", Path(raw).stem).strip("-") or "file"
        suffix = re.sub(r"[^0-9a-zA-Z.]+", "", Path(raw).suffix)[:16]
        return f"{stem}{suffix}"

    def _asset_url(self, *, book_id: str, stored_name: str) -> str:
        return f"/kb/media/{book_id}/{stored_name}"

    def _asset_markdown(self, *, book_id: str, stored_name: str, original_name: str, content_type: str) -> str:
        url = self._asset_url(book_id=book_id, stored_name=stored_name)
        safe_name = original_name or stored_name
        if str(content_type).startswith("image/"):
            alt = Path(safe_name).stem or "image"
            return f"![{alt}]({url})"
        return f"[{safe_name}]({url})"

    def _normalize_node_kind(self, kind: str, *, allow_root: bool = False) -> str:
        normalized = str(kind or "").strip().lower()
        allowed = {"chapter", "page"}
        if allow_root:
            allowed.add("root")
        if normalized not in allowed:
            raise ValueError("节点类型仅支持 chapter 或 page")
        return normalized

    def _is_root_page(self, book: dict[str, Any], page: dict[str, Any]) -> bool:
        return str(page.get("id")) == str(book.get("root_page_id"))

    def _allows_children(self, book: dict[str, Any], page: dict[str, Any]) -> bool:
        if self._is_root_page(book, page):
            return True
        return str(page.get("kind")) == "chapter"

    def _kind_label(self, book: dict[str, Any], page: dict[str, Any]) -> str:
        if self._is_root_page(book, page) or str(page.get("kind")) == "root":
            return "文档首页"
        if str(page.get("kind")) == "chapter":
            return "章节"
        return "正文页"

    def _resolve_parent_page(
        self,
        *,
        book: dict[str, Any],
        catalog: dict[str, Any],
        parent_id: str | None,
    ) -> dict[str, Any]:
        resolved_parent_id = str(parent_id or book["root_page_id"])
        parent = self._page_summary_or_raise(resolved_parent_id, catalog=catalog)
        if str(parent.get("book_id")) != str(book["id"]):
            raise ResourceNotFoundError("父节点不属于当前文档")
        return parent

    def _assert_can_attach_child(
        self,
        *,
        book: dict[str, Any],
        parent: dict[str, Any],
    ) -> None:
        if not self._allows_children(book, parent):
            raise ValueError("只有文档首页或章节节点可以包含子节点")

    def _parent_key(self, value: object) -> str | None:
        if value in (None, "", "None"):
            return None
        return str(value)

    def _book_or_raise(self, book_id: str, *, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
        catalog = catalog or self._load_catalog()
        for book in catalog["books"]:
            if str(book.get("id")) == book_id:
                return self._decorate_book(book)
        raise ResourceNotFoundError("文档不存在")

    def _page_summary_or_raise(
        self,
        page_id: str,
        *,
        catalog: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        catalog = catalog or self._load_catalog()
        page = catalog["pages"].get(page_id)
        if not isinstance(page, dict):
            raise ResourceNotFoundError("页面不存在")
        return self._hydrate_page_summary(page)

    def _get_page_content(self, book_id: str, page_id: str) -> str:
        return self.storage.read_text(self._page_body_key(book_id, page_id)) or ""

    def _save_page_summary(self, summary: dict[str, Any]) -> None:
        self.storage.write_json(
            self._page_meta_key(str(summary["book_id"]), str(summary["id"])),
            summary,
        )

    def _save_page_content(self, summary: dict[str, Any], content: str) -> None:
        self.storage.write_text(
            self._page_body_key(str(summary["book_id"]), str(summary["id"])),
            content,
        )

    def _save_page_revisions(
        self,
        book_id: str,
        page_id: str,
        revisions: list[dict[str, Any]],
    ) -> None:
        self.storage.write_json(self._page_revisions_key(book_id, page_id), revisions)

    def _load_page_revisions(self, book_id: str, page_id: str) -> list[dict[str, Any]]:
        revisions = self.storage.read_json(self._page_revisions_key(book_id, page_id), [])
        return revisions if isinstance(revisions, list) else []

    def _load_page_comments(self, book_id: str, page_id: str) -> list[dict[str, Any]]:
        comments = self.storage.read_json(self._page_comments_key(book_id, page_id), [])
        return comments if isinstance(comments, list) else []

    def _save_page_comments(
        self,
        book_id: str,
        page_id: str,
        comments: list[dict[str, Any]],
    ) -> None:
        self.storage.write_json(self._page_comments_key(book_id, page_id), comments)

    def _list_book_pages(self, book_id: str, *, catalog: dict[str, Any]) -> list[dict[str, Any]]:
        pages = [
            self._hydrate_page_summary(page)
            for page in catalog["pages"].values()
            if isinstance(page, dict) and str(page.get("book_id")) == book_id
        ]
        pages.sort(key=lambda item: (int(item.get("depth", 0)), int(item.get("order", 0)), str(item.get("title", ""))))
        return pages

    def _assert_book_slug_available(
        self,
        catalog: dict[str, Any],
        *,
        slug: str,
        excluding_book_id: str | None = None,
    ) -> None:
        for book in catalog["books"]:
            if excluding_book_id and str(book.get("id")) == excluding_book_id:
                continue
            if str(book.get("slug")) == slug:
                raise ValueError(f"文档 slug 已存在: {slug}")

    def _assert_page_slug_available(
        self,
        catalog: dict[str, Any],
        *,
        book_id: str,
        parent_id: str | None,
        slug: str,
        excluding_page_id: str | None = None,
    ) -> None:
        for page in self._list_book_pages(book_id, catalog=catalog):
            if excluding_page_id and str(page.get("id")) == excluding_page_id:
                continue
            if str(page.get("parent_id") or "") != str(parent_id or ""):
                continue
            if str(page.get("slug")) == slug:
                raise ValueError(f"同级页面 slug 已存在: {slug}")

    def _rebuild_book_tree(self, catalog: dict[str, Any], book_id: str) -> None:
        pages = self._list_book_pages(book_id, catalog=catalog)
        children: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        book = self._book_or_raise(book_id, catalog=catalog)
        for page in pages:
            children[self._parent_key(page.get("parent_id"))].append(page)

        for siblings in children.values():
            siblings.sort(key=lambda item: (int(item.get("order", 0)), str(item.get("title", ""))))

        def walk(parent_id: str | None, parent_segments: list[str], depth: int) -> None:
            for position, page in enumerate(children.get(parent_id, []), start=1):
                page_id = str(page["id"])
                is_root = self._is_root_page(book, page)
                segments = parent_segments if is_root else [*parent_segments, str(page["slug"])]
                page["depth"] = depth
                page["order"] = int(page.get("order", position * 10))
                page["path"] = "/".join(segments)
                catalog["pages"][page_id] = page
                self._save_page_summary(page)
                walk(page_id, segments, depth + 1)

        walk(None, [], 0)

        book["page_count"] = len(pages)
        catalog["books"] = [
            book if str(item.get("id")) == book_id else item for item in catalog["books"]
        ]
        self.storage.write_json(self._book_key(book_id), book)

    def _tree_for_book(self, book_id: str, *, catalog: dict[str, Any]) -> list[dict[str, Any]]:
        pages = self._list_book_pages(book_id, catalog=catalog)
        book = self._book_or_raise(book_id, catalog=catalog)
        by_parent: dict[str | None, list[dict[str, Any]]] = defaultdict(list)
        cloned: dict[str, dict[str, Any]] = {}
        for page in pages:
            page_copy = dict(page)
            page_copy["children"] = []
            page_copy["is_root"] = self._is_root_page(book, page_copy)
            page_copy["kind_label"] = self._kind_label(book, page_copy)
            page_copy["allows_children"] = self._allows_children(book, page_copy)
            cloned[str(page_copy["id"])] = page_copy
            by_parent[self._parent_key(page_copy.get("parent_id"))].append(page_copy)

        for siblings in by_parent.values():
            siblings.sort(key=lambda item: (int(item.get("order", 0)), str(item.get("title", ""))))

        for parent_id, siblings in by_parent.items():
            if parent_id and parent_id in cloned:
                cloned[parent_id]["children"] = siblings

        return by_parent.get(None, [])

    def _collect_descendant_ids(
        self,
        book_id: str,
        page_id: str,
        *,
        catalog: dict[str, Any],
    ) -> set[str]:
        pages = self._list_book_pages(book_id, catalog=catalog)
        children: dict[str | None, list[str]] = defaultdict(list)
        for page in pages:
            children[self._parent_key(page.get("parent_id"))].append(str(page["id"]))

        result: set[str] = set()

        def visit(current_id: str) -> None:
            for child_id in children.get(current_id, []):
                result.add(child_id)
                visit(child_id)

        visit(page_id)
        return result

    def _page_snapshot(self, summary: dict[str, Any]) -> dict[str, Any]:
        page = self._hydrate_page_summary(summary)
        page["content"] = self._get_page_content(str(summary["book_id"]), str(summary["id"]))
        return page

    def _book_snapshot(self, book_id: str, *, catalog: dict[str, Any] | None = None) -> dict[str, Any]:
        catalog = catalog or self._load_catalog()
        book = self._book_or_raise(book_id, catalog=catalog)
        book["tree"] = self._tree_for_book(book_id, catalog=catalog)
        return book

    def _add_revision(
        self,
        summary: dict[str, Any],
        *,
        content: str,
        change_note: str,
        user_id: int,
        username: str,
    ) -> None:
        book_id = str(summary["book_id"])
        page_id = str(summary["id"])
        revisions = self._load_page_revisions(book_id, page_id)
        revisions.append(
            {
                "id": uuid.uuid4().hex,
                "version": int(summary["version"]),
                "change_note": change_note.strip() or "update",
                "content": content,
                "editor_id": user_id,
                "editor_name": username,
                "edited_at": str(summary["updated_at"]),
            }
        )
        self._save_page_revisions(book_id, page_id, revisions)

    def _flatten_tree(self, tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ordered: list[dict[str, Any]] = []

        def walk(nodes: list[dict[str, Any]]) -> None:
            for node in nodes:
                ordered.append(node)
                walk(node.get("children", []))

        walk(tree)
        return ordered

    def _visible_tree(self, book: dict[str, Any], tree: list[dict[str, Any]]) -> list[dict[str, Any]]:
        root_id = str(book["root_page_id"])
        if len(tree) == 1 and str(tree[0].get("id")) == root_id:
            return list(tree[0].get("children", []))
        return [node for node in tree if str(node.get("id")) != root_id]

    def _find_node(self, nodes: list[dict[str, Any]], page_id: str) -> dict[str, Any] | None:
        for node in nodes:
            if str(node.get("id")) == page_id:
                return node
            found = self._find_node(node.get("children", []), page_id)
            if found is not None:
                return found
        return None

    def _flatten_reading_order(
        self,
        *,
        book: dict[str, Any],
        full_tree: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        root = self._find_node(full_tree, str(book["root_page_id"]))
        ordered: list[dict[str, Any]] = []
        if root is not None:
            ordered.append(root)
        ordered.extend(self._flatten_tree(self._visible_tree(book, full_tree)))
        return ordered

    def _breadcrumbs_for_page(
        self,
        *,
        page: dict[str, Any],
        catalog: dict[str, Any],
    ) -> list[dict[str, str]]:
        crumbs: list[dict[str, str]] = []
        current: dict[str, Any] | None = dict(page)
        while current is not None:
            crumbs.append(
                {
                    "id": str(current["id"]),
                    "title": str(current["title"]),
                    "path": str(current.get("path") or ""),
                }
            )
            parent_id = self._parent_key(current.get("parent_id"))
            if parent_id is None:
                break
            current = self._page_summary_or_raise(parent_id, catalog=catalog)
        crumbs.reverse()
        return crumbs

    def _slugify_heading(self, text: str, *, seen: dict[str, int]) -> str:
        base = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "-", text.strip().lower())
        base = re.sub(r"-+", "-", base).strip("-") or "section"
        count = seen.get(base, 0) + 1
        seen[base] = count
        if count == 1:
            return base
        return f"{base}-{count}"

    def _extract_page_headings(self, content: str) -> list[dict[str, Any]]:
        headings: list[dict[str, Any]] = []
        seen: dict[str, int] = {}
        in_code = False

        for raw_line in str(content or "").splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code or not stripped:
                continue

            level = 0
            title = ""
            if stripped.startswith("### "):
                level = 3
                title = stripped[4:]
            elif stripped.startswith("## "):
                level = 2
                title = stripped[3:]
            elif stripped.startswith("# "):
                level = 1
                title = stripped[2:]

            if not level:
                continue

            heading_title = title.strip()
            if not heading_title:
                continue
            headings.append(
                {
                    "level": level,
                    "title": heading_title,
                    "anchor": self._slugify_heading(heading_title, seen=seen),
                }
            )
        return headings

    def _extract_inline_tags(self, content: str) -> list[str]:
        pattern = re.compile(r"(^|[^0-9A-Za-z_\-/\u4e00-\u9fff])#([0-9A-Za-z\u4e00-\u9fff][0-9A-Za-z_\-/\u4e00-\u9fff]{0,39})")
        tags: list[str] = []
        seen: set[str] = set()
        in_code = False

        for raw_line in str(content or "").splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                continue
            if in_code or not stripped or re.match(r"^#{1,6}\s", stripped):
                continue
            candidate_line = re.sub(r"\[\[[^\[\]]+\]\]", "", raw_line)
            for match in pattern.finditer(candidate_line):
                tag = str(match.group(2) or "").strip()
                if not tag or tag in seen:
                    continue
                seen.add(tag)
                tags.append(tag)
        return tags

    def _hydrate_page_summary(self, page: dict[str, Any]) -> dict[str, Any]:
        summary = dict(page)
        if isinstance(summary.get("headings"), list) and isinstance(summary.get("inline_tags"), list):
            return summary
        content = self._get_page_content(str(summary["book_id"]), str(summary["id"]))
        summary["headings"] = self._extract_page_headings(content)
        summary["inline_tags"] = self._extract_inline_tags(content)
        return summary

    def _enrich_page_summary(self, page: dict[str, Any], content: str) -> dict[str, Any]:
        summary = dict(page)
        summary["headings"] = self._extract_page_headings(content)
        summary["inline_tags"] = self._extract_inline_tags(content)
        return summary

    def _tag_href(self, tag: str) -> str:
        return f"/kb/tags/{str(tag).strip()}/"

    def _tag_doc_path(self, tag: str) -> str:
        return f"tags/{str(tag).strip()}.md"

    def _resolve_heading_anchor(
        self,
        page: dict[str, Any],
        heading_title: str,
    ) -> str:
        wanted = str(heading_title or "").strip()
        headings = page.get("headings") or []
        for item in headings:
            if str(item.get("title") or "").strip() == wanted:
                return str(item.get("anchor") or "")
        lowered = wanted.lower()
        for item in headings:
            if str(item.get("title") or "").strip().lower() == lowered:
                return str(item.get("anchor") or "")
        return self._slugify_heading(wanted, seen={})

    def _find_reference_page(
        self,
        pages: list[dict[str, Any]],
        query: str,
    ) -> dict[str, Any] | None:
        raw = str(query or "").strip()
        if raw in {"", "/", "index", "首页"}:
            for page in pages:
                if not str(page.get("path") or "").strip():
                    return page
            return None

        normalized = raw.strip("/")
        for page in pages:
            if str(page.get("path") or "").strip("/") == normalized:
                return page

        title_matches = [page for page in pages if str(page.get("title") or "").strip() == raw]
        if len(title_matches) == 1:
            return title_matches[0]

        slug_matches = [page for page in pages if str(page.get("slug") or "").strip() == normalized]
        if len(slug_matches) == 1:
            return slug_matches[0]

        lowered = raw.lower()
        title_matches = [
            page for page in pages if str(page.get("title") or "").strip().lower() == lowered
        ]
        if len(title_matches) == 1:
            return title_matches[0]

        return None

    def _resolve_reference_token(
        self,
        token: str,
        *,
        book: dict[str, Any],
        current_page: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> str | None:
        raw = str(token or "").strip()
        if not raw:
            return None

        if raw.lower().startswith("tag:") or raw.startswith("标签:"):
            tag = raw.split(":", 1)[1].strip()
            if not tag:
                return None
            return f"[#{tag}]({self._tag_href(tag)})"

        if raw.startswith("#"):
            heading = raw[1:].strip()
            if not heading:
                return None
            anchor = self._resolve_heading_anchor(current_page, heading)
            return f"[{heading}](#{anchor})"

        page_query = raw
        heading_query = ""
        if "#" in raw:
            page_query, heading_query = raw.split("#", 1)

        target = self._find_reference_page(pages, page_query)
        if target is None:
            return None

        url = self._page_href(book_slug=str(book["slug"]), page=target)
        heading = heading_query.strip()
        if heading:
            anchor = self._resolve_heading_anchor(target, heading)
            if anchor:
                url = f"{url}#{anchor}"
            label = heading if str(target.get("id")) == str(current_page.get("id")) else f"{target['title']} / {heading}"
            return f"[{label}]({url})"

        return f"[{str(target['title'])}]({url})"

    def _extract_reference_tokens(self, content: str) -> list[str]:
        seen: set[str] = set()
        tokens: list[str] = []
        for match in re.finditer(r"\[\[([^\[\]]+)\]\]", str(content or "")):
            token = str(match.group(1) or "").strip()
            if token and token not in seen:
                seen.add(token)
                tokens.append(token)
        return tokens

    def _page_reference_graph(
        self,
        *,
        book: dict[str, Any],
        page: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        page_by_id = {str(item["id"]): item for item in pages}
        outgoing: list[dict[str, Any]] = []
        outgoing_seen: set[tuple[str, str]] = set()

        for token in self._extract_reference_tokens(self._get_page_content(str(page["book_id"]), str(page["id"]))):
            raw = str(token).strip()
            if not raw:
                continue
            if raw.lower().startswith("tag:") or raw.startswith("标签:"):
                tag = raw.split(":", 1)[1].strip()
                if tag:
                    key = ("tag", tag)
                    if key not in outgoing_seen:
                        outgoing_seen.add(key)
                        outgoing.append(
                            {
                                "type": "tag",
                                "token": raw,
                                "tag": tag,
                                "href": self._tag_href(tag),
                                "label": f"#{tag}",
                            }
                        )
                continue

            page_query = raw
            heading_query = ""
            if raw.startswith("#"):
                page_query = str(page.get("path") or "")
                heading_query = raw[1:].strip()
            elif "#" in raw:
                page_query, heading_query = raw.split("#", 1)

            target = self._find_reference_page(pages, page_query)
            if target is None:
                continue

            anchor = ""
            heading = heading_query.strip()
            if heading:
                anchor = self._resolve_heading_anchor(target, heading)

            key = (str(target["id"]), anchor)
            if key in outgoing_seen:
                continue
            outgoing_seen.add(key)
            href = self._page_href(book_slug=str(book["slug"]), page=target)
            if anchor:
                href = f"{href}#{anchor}"
            outgoing.append(
                {
                    "type": "heading" if anchor else "page",
                    "token": raw,
                    "page_id": str(target["id"]),
                    "page_title": str(target["title"]),
                    "page_path": str(target.get("path") or ""),
                    "heading": heading or None,
                    "anchor": anchor or None,
                    "href": href,
                    "label": str(target["title"]) if not heading else f"{target['title']} / {heading}",
                    "is_current_page": str(target["id"]) == str(page["id"]),
                }
            )

        incoming: list[dict[str, Any]] = []
        incoming_seen: set[tuple[str, str]] = set()
        for candidate in pages:
            candidate_id = str(candidate["id"])
            if candidate_id == str(page["id"]):
                continue
            content = self._get_page_content(str(candidate["book_id"]), candidate_id)
            for token in self._extract_reference_tokens(content):
                raw = str(token).strip()
                if not raw or raw.lower().startswith("tag:") or raw.startswith("标签:"):
                    continue
                page_query = raw
                heading_query = ""
                if raw.startswith("#"):
                    continue
                if "#" in raw:
                    page_query, heading_query = raw.split("#", 1)
                target = self._find_reference_page(pages, page_query)
                if target is None or str(target["id"]) != str(page["id"]):
                    continue
                heading = heading_query.strip()
                key = (candidate_id, heading)
                if key in incoming_seen:
                    continue
                incoming_seen.add(key)
                href = self._page_href(book_slug=str(book["slug"]), page=candidate)
                incoming.append(
                    {
                        "source_page_id": candidate_id,
                        "source_page_title": str(candidate["title"]),
                        "source_page_path": str(candidate.get("path") or ""),
                        "token": raw,
                        "heading": heading or None,
                        "href": href,
                    }
                )
        return outgoing, incoming

    def _linkify_inline_tags_in_line(self, line: str) -> str:
        pattern = re.compile(r"(^|[^0-9A-Za-z_\-/\u4e00-\u9fff])#([0-9A-Za-z\u4e00-\u9fff][0-9A-Za-z_\-/\u4e00-\u9fff]{0,39})")

        def repl(match: re.Match[str]) -> str:
            prefix = str(match.group(1) or "")
            tag = str(match.group(2) or "").strip()
            return f"{prefix}[#{tag}]({self._tag_href(tag)})"

        return pattern.sub(repl, line)

    def _rewrite_custom_markdown(
        self,
        content: str,
        *,
        book: dict[str, Any],
        current_page: dict[str, Any],
        pages: list[dict[str, Any]],
    ) -> str:
        lines: list[str] = []
        in_code = False
        token_pattern = re.compile(r"\[\[([^\[\]]+)\]\]")
        seen_headings: dict[str, int] = {}

        for raw_line in str(content or "").splitlines():
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                in_code = not in_code
                lines.append(raw_line)
                continue

            if in_code:
                lines.append(raw_line)
                continue

            heading_match = re.match(r"^(#{1,6})\s+(.*?)(\s+\{#[^}]+\})?\s*$", raw_line)
            if heading_match:
                hashes = str(heading_match.group(1) or "")
                heading_title = str(heading_match.group(2) or "").strip()
                explicit_anchor = str(heading_match.group(3) or "").strip()
                if explicit_anchor:
                    lines.append(raw_line)
                    continue
                anchor = self._slugify_heading(heading_title, seen=seen_headings)
                lines.append(f"{hashes} {heading_title} {{#{anchor}}}")
                continue

            tokens: list[str] = []

            def stash_token(match: re.Match[str]) -> str:
                tokens.append(str(match.group(1) or ""))
                return f"__BENFAST_REF_{len(tokens) - 1}__"

            line = token_pattern.sub(stash_token, raw_line)
            line = self._linkify_inline_tags_in_line(line)
            for index, token in enumerate(tokens):
                resolved = self._resolve_reference_token(
                    token,
                    book=book,
                    current_page=current_page,
                    pages=pages,
                )
                line = line.replace(
                    f"__BENFAST_REF_{index}__",
                    resolved or f"[[{token}]]",
                )

            lines.append(line)

        return "\n".join(lines)

    def _book_assets(self, book_id: str) -> list[dict[str, Any]]:
        assets = self.storage.read_json(self._assets_key(book_id), [])
        if not isinstance(assets, list):
            return []
        assets.sort(key=lambda item: str(item.get("uploaded_at", "")), reverse=True)
        return [dict(item) for item in assets if isinstance(item, dict)]

    def _save_book_assets(self, book_id: str, assets: list[dict[str, Any]]) -> None:
        self.storage.write_json(self._assets_key(book_id), assets)

    def _asset_or_raise(self, book_id: str, stored_name: str) -> dict[str, Any]:
        for asset in self._book_assets(book_id):
            if str(asset.get("stored_name")) == stored_name:
                return asset
        raise ResourceNotFoundError("附件不存在")

    def list_book_assets(self, book_id: str) -> list[dict[str, Any]]:
        self._book_or_raise(book_id)
        return self._book_assets(book_id)

    def upload_book_asset(
        self,
        book_id: str,
        *,
        filename: str,
        content_type: str | None,
        payload: bytes,
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        book = self._book_or_raise(book_id)
        if not payload:
            raise ValueError("上传文件不能为空")
        if len(payload) > 25 * 1024 * 1024:
            raise ValueError("单个附件不能超过 25 MB")

        normalized_name = self._normalize_asset_name(filename)
        stored_name = f"{uuid.uuid4().hex[:12]}-{normalized_name}"
        resolved_type = str(content_type or "").strip() or mimetypes.guess_type(normalized_name)[0] or "application/octet-stream"
        asset = {
            "id": uuid.uuid4().hex,
            "book_id": book_id,
            "original_name": Path(str(filename or "file")).name or "file",
            "stored_name": stored_name,
            "content_type": resolved_type,
            "size": len(payload),
            "uploaded_at": self._now_iso(),
            "uploaded_by": user_id,
            "uploaded_by_name": username,
            "url": self._asset_url(book_id=book_id, stored_name=stored_name),
        }
        asset["markdown"] = self._asset_markdown(
            book_id=book_id,
            stored_name=stored_name,
            original_name=str(asset["original_name"]),
            content_type=resolved_type,
        )

        assets = self._book_assets(book_id)
        assets.append(asset)
        self.storage.write_bytes(self._asset_blob_key(book_id, stored_name), payload)
        self._save_book_assets(book_id, assets)
        return asset

    def get_book_asset(self, book_id: str, stored_name: str) -> dict[str, Any]:
        asset = self._asset_or_raise(book_id, stored_name)
        payload = self.storage.read_bytes(self._asset_blob_key(book_id, stored_name))
        if payload is None:
            raise ResourceNotFoundError("附件文件不存在")
        return {
            "meta": asset,
            "content": payload,
        }

    def _site_books(self, catalog: dict[str, Any]) -> list[dict[str, Any]]:
        books = [
            dict(book)
            for book in catalog["books"]
            if str(book.get("published_url") or "").strip()
        ]
        books.sort(
            key=lambda item: (
                str(item.get("last_publish_at") or ""),
                str(item.get("updated_at") or ""),
                str(item.get("title") or ""),
            ),
            reverse=True,
        )
        return books

    def _docs_markdown_path(self, *, book_slug: str, page: dict[str, Any]) -> str:
        path = str(page.get("path") or "").strip("/")
        if not path:
            return f"books/{book_slug}/index.md"
        return f"books/{book_slug}/{path}/index.md"

    def _render_book_cards(
        self,
        books: list[dict[str, Any]],
        *,
        href_prefix: str,
    ) -> str:
        if not books:
            return (
                '<div class="empty-state">'
                "<p>当前还没有已发布文档。先在协作后台完成一份文档，再触发发布。</p>"
                "</div>"
            )

        cards: list[str] = []
        for book in books:
            tags = "".join(
                f'<span class="book-chip">{html.escape(str(tag))}</span>'
                for tag in self._book_keywords(book)
            ) or '<span class="book-chip">未分类</span>'
            summary = html.escape(str(book.get("summary") or "这份文档还没有摘要。"))
            release_at = html.escape(
                self._display_timestamp(book.get("last_publish_at") or "尚未记录")
            )
            page_count = int(book.get("page_count") or 0)
            href = f"{href_prefix}{book['slug']}/"
            cards.append(
                dedent(
                    f"""
                    <a class="book-card" href="{href}">
                      <span class="book-card__eyebrow">正式文档</span>
                      <strong>{html.escape(str(book["title"]))}</strong>
                      <p>{summary}</p>
                      <div class="book-card__meta">
                        <span>{page_count} 个节点</span>
                        <span>{release_at}</span>
                      </div>
                      <div class="book-card__tags">{tags}</div>
                    </a>
                    """
                ).strip()
            )
        return '<div class="book-grid">' + "\n".join(cards) + "</div>"

    def _render_site_index(self, books: list[dict[str, Any]]) -> str:
        latest = (
            html.escape(self._display_timestamp(books[0].get("last_publish_at")))
            if books
            else "-"
        )
        total_nodes = sum(int(book.get("page_count") or 0) for book in books)
        featured = books[:3]
        featured_markup = self._render_book_cards(featured, href_prefix="books/")

        recent_items = []
        for book in books[:5]:
            recent_items.append(
                dedent(
                    f"""
                    <article class="timeline-item">
                      <span class="timeline-item__stamp">{html.escape(self._display_timestamp(book.get("last_publish_at") or "未记录发布时间"))}</span>
                      <strong><a href="books/{book['slug']}/">{html.escape(str(book["title"]))}</a></strong>
                      <p>{html.escape(str(book.get("summary") or "这份文档还没有摘要。"))}</p>
                    </article>
                    """
                ).strip()
            )
        recent_markup = "\n".join(recent_items) or (
            '<div class="empty-state"><p>目前还没有正式发布的文档。先在协作后台完成一份文档，再触发发布。</p></div>'
        )

        lines = [
            "# Benfast 实验室文档站",
            "",
            '<div class="hero-panel hero-panel--portal">',
            "  <div>",
            '    <p class="eyebrow">Lab Documentation</p>',
            "    <h2>统一目录、统一主题、统一发布链路。</h2>",
            "    <p>这里汇总课题组手册、新人入组指南、实验 SOP 与项目知识库。所有正式阅读内容都由同一份 Markdown 文档源构建，目录、TOC、搜索和章节跳转始终保持一致。</p>",
            "  </div>",
            '  <div class="hero-metrics">',
            f'    <div class="hero-metric"><span>已发布文档</span><strong>{len(books)}</strong></div>',
            f'    <div class="hero-metric"><span>总站节点</span><strong>{total_nodes}</strong></div>',
            f'    <div class="hero-metric"><span>最近发布</span><strong>{latest}</strong></div>',
            "  </div>",
            "</div>",
            "",
            "## 重点文档",
            "",
            featured_markup,
            "",
            "## 最新发布",
            "",
            '<div class="timeline-list">',
            recent_markup,
            "</div>",
            "",
            "## 阅读方式",
            "",
            '<div class="portal-grid">',
            '  <article class="portal-card">',
            '    <p class="eyebrow">Browse</p>',
            "    <h3>按目录浏览</h3>",
            "    <p>左侧导航按文档与章节组织，适合完整阅读手册、指南与 SOP。</p>",
            "  </article>",
            '  <article class="portal-card">',
            '    <p class="eyebrow">Search</p>',
            "    <h3>用搜索定位</h3>",
            "    <p>统一总站只保留一套搜索入口，关键词会跨全部已发布文档检索。</p>",
            "  </article>",
            '  <article class="portal-card">',
            '    <p class="eyebrow">Focus</p>',
            "    <h3>跟随本页目录</h3>",
            "    <p>右侧本页目录会根据 Markdown 标题自动生成，长文阅读时可以快速定位段落。</p>",
            "  </article>",
            "</div>",
        ]
        return "\n".join(lines).strip() + "\n"

    def _render_library_page(self, books: list[dict[str, Any]]) -> str:
        return (
            "\n".join(
                [
                    "# 文档库",
                    "",
                    "这里汇总所有已经进入正式阅读站的文档。目录导航、右侧 TOC 和搜索能力都由统一文档站生成。",
                    "",
                    self._render_book_cards(books, href_prefix=""),
                ]
            ).strip()
            + "\n"
        )

    def _docs_stylesheet(self) -> str:
        return dedent(
            """
            :root {
              --labdocs-accent: #00695c;
              --labdocs-accent-deep: #0f3b37;
              --labdocs-surface: linear-gradient(180deg, rgba(250, 248, 242, 0.98) 0%, rgba(242, 238, 229, 0.92) 100%);
              --labdocs-panel: rgba(255, 255, 255, 0.88);
              --labdocs-line: rgba(15, 59, 55, 0.12);
              --labdocs-muted: #5f706d;
              --labdocs-shadow: 0 18px 44px rgba(15, 59, 55, 0.08);
            }

            [data-md-color-scheme="slate"] {
              --labdocs-accent: #80cbc4;
              --labdocs-accent-deep: #d8f3ef;
              --labdocs-surface: linear-gradient(180deg, rgba(22, 31, 43, 0.94) 0%, rgba(14, 21, 30, 0.94) 100%);
              --labdocs-panel: rgba(20, 29, 40, 0.92);
              --labdocs-line: rgba(128, 203, 196, 0.16);
              --labdocs-muted: #b2c0cd;
              --labdocs-shadow: 0 20px 48px rgba(2, 8, 18, 0.32);
            }

            .md-typeset .hero-panel {
              display: grid;
              grid-template-columns: minmax(0, 1fr);
              gap: 1rem;
              padding: 1.2rem 1.3rem;
              border: 1px solid var(--labdocs-line);
              border-radius: 1.4rem;
              background: var(--labdocs-surface);
              box-shadow: var(--labdocs-shadow);
              overflow: hidden;
            }

            .md-typeset .hero-panel--portal {
              margin-bottom: 1rem;
            }

            .md-typeset .hero-panel h2 {
              margin-top: 0;
              font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
              line-height: 1.05;
            }

            .md-typeset .eyebrow {
              margin: 0 0 0.5rem;
              color: var(--labdocs-accent);
              font-size: 0.72rem;
              font-weight: 800;
              letter-spacing: 0.14em;
              text-transform: uppercase;
            }

            .md-typeset .hero-metrics {
              display: grid;
              grid-template-columns: repeat(3, minmax(0, 1fr));
              gap: 0.8rem;
            }

            .md-typeset .hero-panel > div,
            .md-typeset .hero-metric,
            .md-typeset .book-card,
            .md-typeset .timeline-item {
              min-width: 0;
            }

            .md-typeset .hero-metric,
            .md-typeset .book-card {
              border: 1px solid var(--labdocs-line);
              border-radius: 1rem;
              background: var(--labdocs-panel);
            }

            .md-typeset .hero-metric {
              padding: 0.9rem 1rem;
            }

            .md-typeset .hero-metric span,
            .md-typeset .book-card__eyebrow,
            .md-typeset .book-card__meta {
              color: var(--labdocs-muted);
              font-size: 0.78rem;
            }

            .md-typeset .hero-metric strong {
              display: block;
              margin-top: 0.35rem;
              color: var(--labdocs-accent-deep);
              font-size: clamp(1.1rem, 2vw, 1.6rem);
              line-height: 1.25;
              overflow-wrap: anywhere;
              word-break: break-word;
            }

            .md-typeset .book-grid {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
              gap: 1rem;
            }

            .md-typeset .book-card {
              display: grid;
              gap: 0.7rem;
              padding: 1rem;
              color: inherit;
              text-decoration: none;
              transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
            }

            .md-typeset .book-card:hover {
              transform: translateY(-2px);
              border-color: rgba(0, 105, 92, 0.32);
              box-shadow: 0 18px 30px rgba(15, 59, 55, 0.12);
            }

            .md-typeset .book-card strong {
              font-size: 1.15rem;
              line-height: 1.2;
              overflow-wrap: anywhere;
            }

            .md-typeset .book-card p {
              margin: 0;
            }

            .md-typeset .book-card__meta,
            .md-typeset .book-card__tags {
              display: flex;
              flex-wrap: wrap;
              gap: 0.45rem;
            }

            .md-typeset .book-chip {
              display: inline-flex;
              align-items: center;
              padding: 0.25rem 0.6rem;
              border-radius: 999px;
              background: rgba(0, 105, 92, 0.08);
              color: var(--labdocs-accent-deep);
              font-size: 0.74rem;
              font-weight: 700;
            }

            .md-typeset .portal-grid {
              display: grid;
              grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
              gap: 1rem;
            }

            .md-typeset .portal-card,
            .md-typeset .timeline-item {
              padding: 1rem;
              border: 1px solid var(--labdocs-line);
              border-radius: 1rem;
              background: var(--labdocs-panel);
            }

            .md-typeset .portal-card h3,
            .md-typeset .timeline-item strong {
              margin: 0;
              font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
            }

            .md-typeset .portal-card p:last-child,
            .md-typeset .timeline-item p {
              margin-bottom: 0;
            }

            .md-typeset .timeline-list {
              display: grid;
              gap: 0.9rem;
            }

            .md-typeset .timeline-item {
              display: grid;
              gap: 0.5rem;
            }

            .md-typeset .timeline-item__stamp {
              color: var(--labdocs-muted);
              font-size: 0.76rem;
              font-weight: 700;
              letter-spacing: 0.04em;
              overflow-wrap: anywhere;
              word-break: break-word;
            }

            .md-typeset .empty-state {
              padding: 1rem 1.1rem;
              border-left: 4px solid rgba(0, 105, 92, 0.24);
              border-radius: 0.8rem;
              background: var(--labdocs-panel);
            }

            @media (max-width: 900px) {
              .md-typeset .hero-metrics {
                grid-template-columns: 1fr;
              }
            }
            """
        ).strip() + "\n"

    def _write_docs_source_file(self, relative_path: str, content: str) -> None:
        path = self.docs_source_root / "docs" / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _node_nav_entry(self, *, book_slug: str, node: dict[str, Any]) -> dict[str, Any]:
        doc_path = self._docs_markdown_path(book_slug=book_slug, page=node)
        children = node.get("children", [])
        if children:
            return {
                str(node["title"]): [
                    doc_path,
                    *[self._node_nav_entry(book_slug=book_slug, node=child) for child in children],
                ]
            }
        return {str(node["title"]): doc_path}

    def _book_nav_entry(
        self,
        *,
        book: dict[str, Any],
        full_tree: list[dict[str, Any]],
    ) -> dict[str, Any]:
        root = self._find_node(full_tree, str(book["root_page_id"]))
        if root is None:
            return {str(book["title"]): f"books/{book['slug']}/index.md"}

        items: list[Any] = [self._docs_markdown_path(book_slug=str(book["slug"]), page=root)]
        for child in self._visible_tree(book, full_tree):
            items.append(self._node_nav_entry(book_slug=str(book["slug"]), node=child))
        return {str(book["title"]): items}

    def _write_book_markdown(
        self,
        *,
        book: dict[str, Any],
        node: dict[str, Any],
        reference_pages: list[dict[str, Any]],
    ) -> None:
        content = self._get_page_content(str(node["book_id"]), str(node["id"])).strip()
        if not content:
            title = str(node.get("title") or "未命名节点")
            content = f"# {title}\n\n暂无内容。"
        content = self._rewrite_custom_markdown(
            content,
            book=book,
            current_page=node,
            pages=reference_pages,
        )
        relative_path = self._docs_markdown_path(book_slug=str(book["slug"]), page=node)
        self._write_docs_source_file(relative_path, content + "\n")
        for child in node.get("children", []):
            self._write_book_markdown(
                book=book,
                node=child,
                reference_pages=reference_pages,
            )

    def _collect_site_tags(
        self,
        *,
        books: list[dict[str, Any]],
        catalog: dict[str, Any],
    ) -> dict[str, list[dict[str, str]]]:
        tags: dict[str, list[dict[str, str]]] = defaultdict(list)
        for book in books:
            pages = self._list_book_pages(str(book["id"]), catalog=catalog)
            for page in pages:
                for tag in page.get("inline_tags") or []:
                    tags[str(tag)].append(
                        {
                            "book_title": str(book["title"]),
                            "page_title": str(page["title"]),
                            "href": self._page_href(book_slug=str(book["slug"]), page=page),
                        }
                    )
        return dict(tags)

    def _render_tag_index_page(self, tags: dict[str, list[dict[str, str]]]) -> str:
        if not tags:
            return "# 标签索引\n\n当前还没有任何页内标签。\n"

        lines = ["# 标签索引", "", "这里汇总正文里通过 `#标签` 写出的页内标签。", ""]
        for tag in sorted(tags):
            lines.append(f"- [#{tag}]({self._tag_href(tag)})")
        return "\n".join(lines).strip() + "\n"

    def _render_tag_detail_page(self, tag: str, entries: list[dict[str, str]]) -> str:
        lines = [f"# 标签：#{tag}", "", f"共 {len(entries)} 处引用。", ""]
        for entry in entries:
            lines.append(
                f"- [{entry['book_title']} / {entry['page_title']}]({entry['href']})"
            )
        return "\n".join(lines).strip() + "\n"

    def _write_tag_pages(
        self,
        *,
        books: list[dict[str, Any]],
        catalog: dict[str, Any],
    ) -> None:
        tags = self._collect_site_tags(books=books, catalog=catalog)
        self._write_docs_source_file("tags/index.md", self._render_tag_index_page(tags))
        for tag, entries in tags.items():
            self._write_docs_source_file(
                self._tag_doc_path(tag),
                self._render_tag_detail_page(tag, entries),
            )

    def _render_mkdocs_config(self, *, nav: list[dict[str, Any]]) -> str:
        config = {
            "site_name": "Benfast 实验室文档站",
            "site_description": "由 Benfast 协作源统一构建的实验室总文档站",
            "site_author": "Ben Group",
            "docs_dir": str(self.docs_source_root / "docs"),
            "site_dir": str(self.docs_site_dir),
            "use_directory_urls": True,
            "theme": {
                "name": "material",
                "language": "zh",
                "icon": {"logo": "material/bookshelf"},
                "palette": [
                    {
                        "media": "(prefers-color-scheme: light)",
                        "scheme": "default",
                        "primary": "teal",
                        "accent": "amber",
                        "toggle": {
                            "icon": "material/weather-night",
                            "name": "切换到深色模式",
                        },
                    },
                    {
                        "media": "(prefers-color-scheme: dark)",
                        "scheme": "slate",
                        "primary": "teal",
                        "accent": "amber",
                        "toggle": {
                            "icon": "material/weather-sunny",
                            "name": "切换到浅色模式",
                        },
                    },
                ],
                "font": {"text": "Noto Sans SC", "code": "JetBrains Mono"},
                "features": [
                    "content.code.copy",
                    "navigation.footer",
                    "navigation.indexes",
                    "navigation.instant",
                    "navigation.sections",
                    "navigation.tabs",
                    "navigation.top",
                    "search.highlight",
                    "search.suggest",
                    "toc.follow",
                ],
            },
            "plugins": ["search"],
            "markdown_extensions": [
                "admonition",
                "attr_list",
                "def_list",
                "footnotes",
                "md_in_html",
                "tables",
                {"toc": {"permalink": True, "title": "本页目录"}},
                "pymdownx.details",
                {
                    "pymdownx.highlight": {
                        "anchor_linenums": True,
                        "line_spans": "__span",
                        "pygments_lang_class": True,
                    }
                },
                "pymdownx.inlinehilite",
                "pymdownx.magiclink",
                {
                    "pymdownx.superfences": {
                        "custom_fences": [
                            {
                                "name": "mermaid",
                                "class": "mermaid",
                                "format": "pymdownx.superfences.fence_code_format",
                            }
                        ]
                    }
                },
                {"pymdownx.tabbed": {"alternate_style": True}},
                {"pymdownx.tasklist": {"custom_checkbox": True}},
            ],
            "extra_css": ["stylesheets/labdocs.css"],
            "nav": nav,
            "strict": False,
        }
        return yaml.safe_dump(config, allow_unicode=True, sort_keys=False)

    def _mkdocs_command(self) -> list[str]:
        direct_binary = Path(settings.BASE_DIR) / ".venv" / "bin" / "mkdocs"
        if direct_binary.exists():
            return [str(direct_binary)]
        return ["uv", "run", "--group", "docs", "mkdocs"]

    def _run_unified_site_build(self, config_path: Path) -> None:
        command = [*self._mkdocs_command(), "build", "--clean", "-f", str(config_path)]
        result = subprocess.run(
            command,
            cwd=settings.BASE_DIR,
            env={**os.environ, "PYTHONUTF8": "1"},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            output = (result.stdout or "").strip()
            raise RuntimeError(f"总文档站构建失败。\n{output[-4000:]}")

    def _rebuild_unified_docs_site(self, catalog: dict[str, Any]) -> None:
        books = self._site_books(catalog)
        shutil.rmtree(self.docs_source_root, ignore_errors=True)
        (self.docs_source_root / "docs" / "stylesheets").mkdir(parents=True, exist_ok=True)

        self._write_docs_source_file("index.md", self._render_site_index(books))
        self._write_docs_source_file("books/index.md", self._render_library_page(books))
        self._write_docs_source_file("stylesheets/labdocs.css", self._docs_stylesheet())
        self._write_tag_pages(books=books, catalog=catalog)

        nav: list[dict[str, Any]] = [
            {"首页": "index.md"},
            {"文档库": "books/index.md"},
        ]
        for book in books:
            full_tree = self._tree_for_book(str(book["id"]), catalog=catalog)
            reference_pages = self._list_book_pages(str(book["id"]), catalog=catalog)
            root = self._find_node(full_tree, str(book["root_page_id"]))
            if root is None:
                continue
            self._write_book_markdown(
                book=book,
                node=root,
                reference_pages=reference_pages,
            )
            nav.append(self._book_nav_entry(book=book, full_tree=full_tree))

        config_path = self.docs_source_root / "mkdocs.generated.yml"
        config_path.write_text(self._render_mkdocs_config(nav=nav), encoding="utf-8")
        self._run_unified_site_build(config_path)

    def list_books(self, *, q: str | None = None) -> list[dict[str, Any]]:
        catalog = self._load_catalog()
        keyword = str(q or "").strip().lower()
        books: list[dict[str, Any]] = []
        for book in catalog["books"]:
            haystack = " ".join(
                [
                    str(book.get("title", "")),
                    str(book.get("slug", "")),
                    str(book.get("description", "")),
                    str(book.get("summary", "")),
                    " ".join(self._book_keywords(book)),
                ]
            ).lower()
            if keyword and keyword not in haystack:
                continue
            books.append(self._decorate_book(book))
        books.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
        return books

    def get_book(self, book_id: str) -> dict[str, Any]:
        return self._book_snapshot(book_id)

    def create_book(
        self,
        *,
        title: str,
        slug: str,
        description: str,
        summary: str,
        keywords: list[str],
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        normalized_slug = self._normalize_slug(slug)
        self._assert_book_slug_available(catalog, slug=normalized_slug)

        now = self._now_iso()
        book_id = uuid.uuid4().hex
        root_page_id = uuid.uuid4().hex
        root_content = (
            f"# {title.strip()}\n\n"
            "这里是当前文档的首页。\n\n"
            "## 如何使用这份文档\n\n"
            "- 先浏览 OUTLINE 了解整体结构\n"
            "- 章节用于组织结构，正文页用于承载具体内容\n"
            "- 发布后可通过文档级目录和页内目录快速跳转\n"
            "- 支持 [[#如何使用这份文档]]、[[index]]、[[标签:示例标签]] 与 #示例标签 语法\n"
        )
        root_page = {
            "id": root_page_id,
            "book_id": book_id,
            "parent_id": None,
            "title": title.strip(),
            "slug": "index",
            "kind": "root",
            "order": 10,
            "depth": 0,
            "path": "",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "created_by_name": username,
            "updated_by": user_id,
            "updated_by_name": username,
        }
        root_page = self._enrich_page_summary(root_page, root_content)
        book = {
            "id": book_id,
            "slug": normalized_slug,
            "title": title.strip(),
            "description": description.strip(),
            "summary": summary.strip(),
            "keywords": self._normalize_tags(keywords),
            "root_page_id": root_page_id,
            "page_count": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "created_by_name": username,
            "updated_by": user_id,
            "updated_by_name": username,
            "last_publish_at": None,
            "last_publish_release_id": None,
            "published_url": None,
        }

        catalog["books"].append(book)
        catalog["pages"][root_page_id] = root_page
        self._save_catalog(catalog)
        self.storage.write_json(self._book_key(book_id), book)
        self._save_page_summary(root_page)
        self._save_page_content(root_page, root_content)
        self._save_page_comments(book_id, root_page_id, [])
        self._add_revision(
            root_page,
            content=root_content,
            change_note="create root page",
            user_id=user_id,
            username=username,
        )
        return self._book_snapshot(book_id, catalog=catalog)

    def update_book(
        self,
        book_id: str,
        *,
        title: str | None,
        slug: str | None,
        description: str | None,
        summary: str | None,
        keywords: list[str] | None,
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        book = self._book_or_raise(book_id, catalog=catalog)
        if slug is not None:
            normalized_slug = self._normalize_slug(slug)
            self._assert_book_slug_available(
                catalog,
                slug=normalized_slug,
                excluding_book_id=book_id,
            )
            book["slug"] = normalized_slug
        if title is not None:
            book["title"] = title.strip()
        if description is not None:
            book["description"] = description.strip()
        if summary is not None:
            book["summary"] = summary.strip()
        if keywords is not None:
            book["keywords"] = self._normalize_tags(keywords)
        book["updated_at"] = self._now_iso()
        book["updated_by"] = user_id
        book["updated_by_name"] = username

        catalog["books"] = [
            book if str(item.get("id")) == book_id else item for item in catalog["books"]
        ]
        self._save_catalog(catalog)
        self.storage.write_json(self._book_key(book_id), book)
        return self._book_snapshot(book_id, catalog=catalog)

    def list_reference_targets(
        self,
        book_id: str,
        *,
        page_id: str | None = None,
        q: str | None = None,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        book = self._book_or_raise(book_id, catalog=catalog)
        pages = self._list_book_pages(book_id, catalog=catalog)
        current_page = self._page_summary_or_raise(page_id, catalog=catalog) if page_id else None
        if current_page is not None and str(current_page.get("book_id")) != str(book_id):
            raise ResourceNotFoundError("页面不属于当前文档")
        keyword = str(q or "").strip().lower()

        page_entries: list[dict[str, Any]] = []
        for page in pages:
            entry = {
                "id": str(page["id"]),
                "title": str(page["title"]),
                "slug": str(page["slug"]),
                "path": str(page.get("path") or ""),
                "kind": str(page.get("kind") or "page"),
                "kind_label": str(page.get("kind_label") or self._kind_label(book, page)),
                "href": self._page_href(book_slug=str(book["slug"]), page=page),
                "token": str(page.get("path") or "") or "index",
                "headings": [
                    {
                        "title": str(item.get("title") or ""),
                        "anchor": str(item.get("anchor") or ""),
                        "token": (
                            f"{str(page.get('path') or '')}#{str(item.get('title') or '')}"
                            if str(page.get("path") or "").strip()
                            else f"index#{str(item.get('title') or '')}"
                        ),
                    }
                    for item in page.get("headings") or []
                ],
            }
            haystack = " ".join(
                [
                    entry["title"],
                    entry["slug"],
                    entry["path"],
                    " ".join(str(item["title"]) for item in entry["headings"]),
                ]
            ).lower()
            if keyword and keyword not in haystack:
                continue
            page_entries.append(entry)

        tag_map: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for page in pages:
            for tag in page.get("inline_tags") or []:
                normalized = str(tag).strip()
                if not normalized:
                    continue
                tag_map[normalized].append(
                    {
                        "page_id": str(page["id"]),
                        "page_title": str(page["title"]),
                        "page_path": str(page.get("path") or ""),
                        "href": self._page_href(book_slug=str(book["slug"]), page=page),
                    }
                )
        tag_entries: list[dict[str, Any]] = []
        for normalized in sorted(tag_map):
            entries = tag_map[normalized]
            haystack = " ".join(
                [
                    normalized,
                    *[
                        f"{str(item['page_title'])} {str(item['page_path'])}"
                        for item in entries
                    ],
                ]
            ).lower()
            if keyword and keyword not in haystack:
                continue
            tag_entries.append(
                {
                    "tag": normalized,
                    "token": f"标签:{normalized}",
                    "hash_token": f"#{normalized}",
                    "href": self._tag_href(normalized),
                    "count": len(entries),
                    "entries": entries,
                }
            )

        references = {"outgoing": [], "incoming": []}
        if current_page is not None:
            references["outgoing"], references["incoming"] = self._page_reference_graph(
                book=book,
                page=current_page,
                pages=pages,
            )

        return {
            "book": {
                "id": str(book["id"]),
                "slug": str(book["slug"]),
                "title": str(book["title"]),
            },
            "current_page_id": str(current_page["id"]) if current_page else None,
            "pages": page_entries,
            "tags": tag_entries,
            "references": references,
        }

    def get_book_tree(self, book_id: str) -> list[dict[str, Any]]:
        catalog = self._load_catalog()
        self._book_or_raise(book_id, catalog=catalog)
        return self._tree_for_book(book_id, catalog=catalog)

    def create_page(
        self,
        book_id: str,
        *,
        parent_id: str | None,
        title: str,
        slug: str,
        kind: str,
        order: int | None,
        content: str,
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        book = self._book_or_raise(book_id, catalog=catalog)
        normalized_kind = self._normalize_node_kind(kind)
        normalized_slug = self._normalize_slug(slug)
        parent = self._resolve_parent_page(book=book, catalog=catalog, parent_id=parent_id)
        self._assert_can_attach_child(book=book, parent=parent)
        resolved_parent_id = str(parent["id"])
        self._assert_page_slug_available(
            catalog,
            book_id=book_id,
            parent_id=resolved_parent_id,
            slug=normalized_slug,
        )

        now = self._now_iso()
        page_id = uuid.uuid4().hex
        page = {
            "id": page_id,
            "book_id": book_id,
            "parent_id": resolved_parent_id,
            "title": title.strip(),
            "slug": normalized_slug,
            "kind": normalized_kind,
            "order": int(order if order is not None else 999),
            "depth": 0,
            "path": "",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "created_by": user_id,
            "created_by_name": username,
            "updated_by": user_id,
            "updated_by_name": username,
        }
        page = self._enrich_page_summary(page, content)
        catalog["pages"][page_id] = page
        book["updated_at"] = now
        book["updated_by"] = user_id
        book["updated_by_name"] = username
        catalog["books"] = [
            book if str(item.get("id")) == book_id else item for item in catalog["books"]
        ]
        self._rebuild_book_tree(catalog, book_id)
        self._save_catalog(catalog)
        self.storage.write_json(self._book_key(book_id), book)
        self._save_page_content(page, content)
        self._save_page_comments(book_id, page_id, [])
        self._add_revision(
            page,
            content=content,
            change_note=f"create {normalized_kind}",
            user_id=user_id,
            username=username,
        )
        return self.get_page(page_id)

    def get_page(self, page_id: str) -> dict[str, Any]:
        catalog = self._load_catalog()
        page = self._page_summary_or_raise(page_id, catalog=catalog)
        return self._page_snapshot(page)

    def update_page(
        self,
        page_id: str,
        *,
        expected_version: int,
        title: str | None,
        slug: str | None,
        content: str,
        change_note: str,
        user_id: int,
        username: str,
        is_superuser: bool,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        page = self._page_summary_or_raise(page_id, catalog=catalog)
        lock = self.get_lock(page_id)
        if lock and int(lock.get("holder_id", 0)) != user_id and not is_superuser:
            raise LockConflictError("页面当前被其他成员锁定", lock=lock)

        current_version = int(page.get("version", 0))
        if current_version != expected_version:
            raise VersionConflictError(
                "版本冲突：页面已被更新，请刷新后再提交",
                current_version=current_version,
            )

        if slug is not None:
            normalized_slug = self._normalize_slug(slug)
            self._assert_page_slug_available(
                catalog,
                book_id=str(page["book_id"]),
                parent_id=page.get("parent_id"),
                slug=normalized_slug,
                excluding_page_id=page_id,
            )
            page["slug"] = normalized_slug
        if title is not None:
            page["title"] = title.strip()

        page["version"] = current_version + 1
        page["updated_at"] = self._now_iso()
        page["updated_by"] = user_id
        page["updated_by_name"] = username
        page = self._enrich_page_summary(page, content)
        catalog["pages"][page_id] = page

        book = self._book_or_raise(str(page["book_id"]), catalog=catalog)
        book["updated_at"] = str(page["updated_at"])
        book["updated_by"] = user_id
        book["updated_by_name"] = username
        catalog["books"] = [
            book if str(item.get("id")) == str(book["id"]) else item
            for item in catalog["books"]
        ]

        self._rebuild_book_tree(catalog, str(page["book_id"]))
        self._save_catalog(catalog)
        updated_page = self._page_summary_or_raise(page_id, catalog=catalog)
        self._save_page_content(updated_page, content)
        self._add_revision(
            updated_page,
            content=content,
            change_note=change_note,
            user_id=user_id,
            username=username,
        )
        return self._page_snapshot(updated_page)

    def move_page(
        self,
        page_id: str,
        *,
        parent_id: str | None,
        order: int,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        page = self._page_summary_or_raise(page_id, catalog=catalog)
        book_id = str(page["book_id"])
        book = self._book_or_raise(book_id, catalog=catalog)
        if self._is_root_page(book, page):
            raise ValueError("文档首页不能移动")

        parent = self._resolve_parent_page(book=book, catalog=catalog, parent_id=parent_id)
        resolved_parent_id = str(parent["id"])
        if resolved_parent_id == page_id:
            raise ValueError("页面不能移动到自己下面")
        descendants = self._collect_descendant_ids(book_id, page_id, catalog=catalog)
        if resolved_parent_id in descendants:
            raise ValueError("页面不能移动到自己的子页面下面")
        self._assert_can_attach_child(book=book, parent=parent)

        self._assert_page_slug_available(
            catalog,
            book_id=book_id,
            parent_id=resolved_parent_id,
            slug=str(page["slug"]),
            excluding_page_id=page_id,
        )
        page["parent_id"] = resolved_parent_id
        page["order"] = int(order)
        catalog["pages"][page_id] = page
        self._rebuild_book_tree(catalog, book_id)
        self._save_catalog(catalog)
        return self._page_snapshot(self._page_summary_or_raise(page_id, catalog=catalog))

    def list_page_revisions(self, page_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        summary = self._page_summary_or_raise(page_id)
        revisions = self._load_page_revisions(str(summary["book_id"]), page_id)
        revisions.sort(key=lambda item: int(item.get("version", 0)), reverse=True)
        return revisions[: max(1, min(limit, 200))]

    def list_page_comments(self, page_id: str) -> list[dict[str, Any]]:
        summary = self._page_summary_or_raise(page_id)
        comments = self._load_page_comments(str(summary["book_id"]), page_id)
        comments.sort(key=lambda item: str(item.get("created_at", "")))
        return comments

    def add_page_comment(
        self,
        page_id: str,
        *,
        content: str,
        anchor: str | None,
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        summary = self._page_summary_or_raise(page_id)
        comments = self._load_page_comments(str(summary["book_id"]), page_id)
        comment = {
            "id": uuid.uuid4().hex,
            "content": content.strip(),
            "anchor": str(anchor or "").strip() or None,
            "author_id": user_id,
            "author_name": username,
            "created_at": self._now_iso(),
        }
        comments.append(comment)
        self._save_page_comments(str(summary["book_id"]), page_id, comments)
        return comment

    def get_lock(self, page_id: str) -> dict[str, Any] | None:
        self._page_summary_or_raise(page_id)
        locks = self._load_locks()
        return locks.get(page_id)

    def acquire_lock(
        self,
        page_id: str,
        *,
        user_id: int,
        username: str,
        ttl_minutes: int,
    ) -> dict[str, Any]:
        self._page_summary_or_raise(page_id)
        locks = self._load_locks()
        existing = locks.get(page_id)
        if existing and int(existing.get("holder_id", 0)) != user_id:
            raise LockConflictError("页面正在被其他成员编辑", lock=existing)

        now = datetime.now(UTC)
        lock = {
            "page_id": page_id,
            "holder_id": user_id,
            "holder_name": username,
            "acquired_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=ttl_minutes)).isoformat(),
        }
        locks[page_id] = lock
        self._save_locks(locks)
        return lock

    def release_lock(
        self,
        page_id: str,
        *,
        user_id: int,
        is_superuser: bool,
    ) -> dict[str, Any]:
        self._page_summary_or_raise(page_id)
        locks = self._load_locks()
        existing = locks.get(page_id)
        if not existing:
            return {"released": False, "lock": None}
        if int(existing.get("holder_id", 0)) != user_id and not is_superuser:
            raise PermissionDeniedError("仅锁持有者或管理员可以释放编辑锁")
        del locks[page_id]
        self._save_locks(locks)
        return {"released": True, "lock": existing}

    def _render_inline_markdown(self, text: str) -> str:
        rendered = html.escape(text)
        rendered = re.sub(r"`([^`]+)`", r"<code>\1</code>", rendered)
        rendered = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", rendered)
        rendered = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", rendered)
        rendered = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" target="_blank" rel="noreferrer">\1</a>',
            rendered,
        )
        return rendered

    def _markdown_to_html(self, content: str) -> str:
        html_content, _ = self._markdown_to_html_with_toc(content)
        return html_content

    def _markdown_to_html_with_toc(self, content: str) -> tuple[str, list[dict[str, Any]]]:
        lines = content.splitlines()
        blocks: list[str] = []
        toc: list[dict[str, Any]] = []
        paragraph: list[str] = []
        list_items: list[str] = []
        in_code = False
        code_lines: list[str] = []
        seen_anchors: dict[str, int] = {}

        def flush_paragraph() -> None:
            nonlocal paragraph
            if paragraph:
                blocks.append(
                    "<p>" + "<br />".join(self._render_inline_markdown(line) for line in paragraph) + "</p>"
                )
                paragraph = []

        def flush_list() -> None:
            nonlocal list_items
            if list_items:
                items = "".join(f"<li>{self._render_inline_markdown(item)}</li>" for item in list_items)
                blocks.append(f"<ul>{items}</ul>")
                list_items = []

        def append_heading(level: int, raw_text: str) -> None:
            title = raw_text.strip()
            anchor = self._slugify_heading(title, seen=seen_anchors)
            toc.append(
                {
                    "level": level,
                    "title": title,
                    "anchor": anchor,
                }
            )
            blocks.append(
                f'<h{level} id="{html.escape(anchor)}">{self._render_inline_markdown(title)}</h{level}>'
            )

        for raw_line in lines:
            line = raw_line.rstrip()
            if line.startswith("```"):
                flush_paragraph()
                flush_list()
                if in_code:
                    blocks.append(
                        "<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>"
                    )
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                continue

            if in_code:
                code_lines.append(raw_line)
                continue

            stripped = line.strip()
            if not stripped:
                flush_paragraph()
                flush_list()
                continue

            if stripped.startswith("### "):
                flush_paragraph()
                flush_list()
                append_heading(3, stripped[4:])
                continue
            if stripped.startswith("## "):
                flush_paragraph()
                flush_list()
                append_heading(2, stripped[3:])
                continue
            if stripped.startswith("# "):
                flush_paragraph()
                flush_list()
                append_heading(1, stripped[2:])
                continue
            if stripped.startswith("- "):
                flush_paragraph()
                list_items.append(stripped[2:])
                continue

            flush_list()
            paragraph.append(stripped)

        flush_paragraph()
        flush_list()
        if in_code:
            blocks.append("<pre><code>" + html.escape("\n".join(code_lines)) + "</code></pre>")
        return "\n".join(blocks), toc

    def _page_href(self, *, book_slug: str, page: dict[str, Any]) -> str:
        path = str(page.get("path") or "")
        return f"/kb/books/{book_slug}/" if not path else f"/kb/books/{book_slug}/{path}/"

    def _render_sidebar(self, nodes: list[dict[str, Any]], *, book_slug: str, current_page_id: str) -> str:
        items: list[str] = []
        for node in nodes:
            current = " is-current" if str(node["id"]) == current_page_id else ""
            url = self._page_href(book_slug=book_slug, page=node)
            children_html = self._render_sidebar(
                node.get("children", []),
                book_slug=book_slug,
                current_page_id=current_page_id,
            )
            items.append(
                "<li>"
                f'<a class="sidebar-link{current}" href="{url}">'
                f'<span class="sidebar-kind">{html.escape(str(node.get("kind_label") or "节点"))}</span>'
                f'<strong>{html.escape(str(node["title"]))}</strong>'
                f"</a>"
                f"{children_html}"
                "</li>"
            )
        if not items:
            return ""
        return "<ul class=\"sidebar-tree\">" + "".join(items) + "</ul>"

    def _render_toc(self, toc: list[dict[str, Any]]) -> str:
        if not toc:
            return '<p class="toc-empty">当前页面没有可生成的页内目录。</p>'

        items = []
        for item in toc:
            items.append(
                f'<li><a class="toc-link toc-level-{int(item["level"])}" href="#{html.escape(str(item["anchor"]))}">'
                f"{html.escape(str(item['title']))}</a></li>"
            )
        return "<ul class=\"toc-list\">" + "".join(items) + "</ul>"

    def _render_child_links(self, *, book: dict[str, Any], children: list[dict[str, Any]]) -> str:
        if not children:
            return ""

        cards = []
        for child in children:
            cards.append(
                "<a class=\"child-card\" "
                f'href="{self._page_href(book_slug=str(book["slug"]), page=child)}">'
                f'<span>{html.escape(str(child.get("kind_label") or "节点"))}</span>'
                f'<strong>{html.escape(str(child["title"]))}</strong>'
                "</a>"
            )
        return (
            "<section class=\"child-shelf\">"
            "<p class=\"eyebrow\">Chapter Flow</p>"
            "<h2>本层目录</h2>"
            f"<div class=\"child-grid\">{''.join(cards)}</div>"
            "</section>"
        )

    def _render_published_page(
        self,
        *,
        book: dict[str, Any],
        page: dict[str, Any],
        navigation_tree: list[dict[str, Any]],
        breadcrumbs: list[dict[str, str]],
        child_nodes: list[dict[str, Any]],
        previous_page: dict[str, Any] | None,
        next_page: dict[str, Any] | None,
    ) -> str:
        page_url = self._page_href(book_slug=str(book["slug"]), page=page)
        markdown_html, toc = self._markdown_to_html_with_toc(
            self._get_page_content(str(page["book_id"]), str(page["id"]))
        )

        def link_for(item: dict[str, Any] | None, label: str) -> str:
            if item is None:
                return ""
            href = self._page_href(book_slug=str(book["slug"]), page=item)
            return f'<a class="pager-link" href="{href}">{label}: {html.escape(str(item["title"]))}</a>'

        breadcrumb_parts = [f'<a href="/kb/books/{book["slug"]}/">首页</a>']
        for crumb in breadcrumbs[1:-1]:
            breadcrumb_parts.append(
                f'<a href="{self._page_href(book_slug=str(book["slug"]), page=crumb)}">{html.escape(str(crumb["title"]))}</a>'
            )
        if len(breadcrumbs) > 1:
            breadcrumb_parts.append(f"<span>{html.escape(str(breadcrumbs[-1]['title']))}</span>")
        else:
            breadcrumb_parts.append("<span>文档首页</span>")

        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{html.escape(str(page["title"]))} | {html.escape(str(book["title"]))}</title>
    <link rel="stylesheet" href="/kb/books/{book['slug']}/assets/book.css" />
  </head>
  <body>
    <div class="published-shell">
      <aside class="published-sidebar">
        <p class="eyebrow">Published Document</p>
        <a class="book-home-link" href="/kb/books/{book['slug']}/">{html.escape(str(book["title"]))}</a>
        <p class="summary">{html.escape(str(book.get("summary", "")))}</p>
        <a class="workspace-link" href="/workspace/">返回协作区</a>
        <div class="sidebar-block">
          <p class="sidebar-title">OUTLINE</p>
          {self._render_sidebar(navigation_tree, book_slug=str(book["slug"]), current_page_id=str(page["id"]))}
        </div>
      </aside>
      <main class="published-main">
        <div class="content-head">
          <p class="eyebrow">/{html.escape(page_url.strip("/"))}</p>
          <div class="breadcrumbs">{' / '.join(breadcrumb_parts)}</div>
          <h1>{html.escape(str(page["title"]))}</h1>
          <p class="meta">{html.escape(str(page.get("kind_label") or "页面"))} · 版本 v{page["version"]} · 最近更新 {html.escape(str(page["updated_at"]))} · 编辑者 {html.escape(str(page["updated_by_name"]))}</p>
        </div>
        {self._render_child_links(book=book, children=child_nodes)}
        <article class="markdown-body">
          {markdown_html}
        </article>
        <nav class="pager">
          {link_for(previous_page, "上一页")}
          {link_for(next_page, "下一页")}
        </nav>
      </main>
      <aside class="toc-rail">
        <p class="eyebrow">Page TOC</p>
        <h2>本页目录</h2>
        {self._render_toc(toc)}
      </aside>
    </div>
  </body>
</html>
"""

    def _published_styles(self) -> str:
        return """
:root {
  --ink: #172033;
  --muted: #68758d;
  --line: rgba(23, 32, 51, 0.12);
  --paper: #fffdf8;
  --paper-strong: #f6f1e7;
  --accent: #8a5a00;
  --accent-deep: #5b3b00;
  --bg: radial-gradient(circle at top left, #f7f1df 0%, #efe7d3 30%, #e7e9ef 100%);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  color: var(--ink);
  background: var(--bg);
  font-family: "Avenir Next", "PingFang SC", "Noto Sans SC", sans-serif;
}
a { color: inherit; }
.published-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr) 260px;
}
.published-sidebar,
.toc-rail {
  padding: 28px 24px;
  background: rgba(255, 253, 248, 0.82);
  backdrop-filter: blur(18px);
}
.published-sidebar {
  border-right: 1px solid var(--line);
}
.toc-rail {
  border-left: 1px solid var(--line);
}
.eyebrow {
  margin: 0 0 8px;
  font-size: 12px;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--accent);
}
.summary, .meta, .toc-empty {
  color: var(--muted);
}
.book-home-link {
  display: inline-block;
  font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
  font-size: 34px;
  line-height: 1.05;
  text-decoration: none;
}
.workspace-link {
  display: inline-block;
  margin: 12px 0 18px;
  padding: 8px 12px;
  border-radius: 999px;
  border: 1px solid var(--line);
  text-decoration: none;
}
.sidebar-block {
  display: grid;
  gap: 10px;
}
.sidebar-title {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: var(--muted);
  letter-spacing: 0.08em;
}
.sidebar-tree {
  list-style: none;
  margin: 0;
  padding-left: 0;
}
.sidebar-tree ul {
  margin: 8px 0 0 14px;
  padding-left: 14px;
  border-left: 1px solid rgba(23, 32, 51, 0.12);
}
.sidebar-tree > li { margin: 10px 0; }
.sidebar-link {
  display: grid;
  gap: 4px;
  padding: 10px 12px;
  border-radius: 14px;
  border: 1px solid rgba(23, 32, 51, 0.1);
  background: rgba(255, 255, 255, 0.62);
  text-decoration: none;
}
.sidebar-link strong {
  font-size: 15px;
}
.sidebar-kind {
  font-size: 11px;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--accent);
}
.sidebar-link.is-current {
  background: var(--accent-deep);
  color: #fff;
}
.sidebar-link.is-current .sidebar-kind {
  color: rgba(255, 255, 255, 0.76);
}
.published-main {
  padding: 40px min(5vw, 56px);
}
.content-head {
  margin-bottom: 24px;
}
.content-head h1 {
  margin: 8px 0;
  font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
  font-size: clamp(2.2rem, 4vw, 3.6rem);
  line-height: 0.98;
}
.breadcrumbs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  color: var(--muted);
}
.markdown-body {
  max-width: 860px;
  padding: 28px 32px;
  border: 1px solid var(--line);
  border-radius: 24px;
  background: var(--paper);
  box-shadow: 0 24px 60px rgba(29, 39, 58, 0.08);
}
.markdown-body h1,
.markdown-body h2,
.markdown-body h3 {
  margin-top: 1.2em;
  scroll-margin-top: 20px;
  font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
}
.markdown-body pre {
  padding: 16px;
  overflow: auto;
  border-radius: 14px;
  background: #1e2535;
  color: #eef2ff;
}
.markdown-body code {
  padding: 2px 6px;
  border-radius: 6px;
  background: var(--paper-strong);
}
.child-shelf {
  margin-bottom: 18px;
}
.child-shelf h2,
.toc-rail h2 {
  margin: 0 0 10px;
  font-family: "Iowan Old Style", "Baskerville", "Songti SC", serif;
}
.child-grid {
  display: grid;
  gap: 12px;
}
.child-card {
  display: grid;
  gap: 6px;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid var(--line);
  background: rgba(255, 255, 255, 0.68);
  text-decoration: none;
}
.child-card span {
  color: var(--accent);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}
.toc-list {
  display: grid;
  gap: 8px;
}
.toc-link {
  display: block;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.56);
  border: 1px solid rgba(23, 32, 51, 0.08);
  text-decoration: none;
}
.toc-level-2 { margin-left: 12px; }
.toc-level-3 { margin-left: 24px; }
.pager {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}
.pager-link {
  text-decoration: none;
  padding: 10px 14px;
  border-radius: 12px;
  background: rgba(255, 253, 248, 0.9);
  border: 1px solid var(--line);
}
@media (max-width: 1200px) {
  .published-shell {
    grid-template-columns: 280px 1fr;
  }
  .toc-rail {
    grid-column: 1 / -1;
    border-left: none;
    border-top: 1px solid var(--line);
  }
}
@media (max-width: 900px) {
  .published-shell { grid-template-columns: 1fr; }
  .published-sidebar {
    border-right: none;
    border-bottom: 1px solid var(--line);
  }
  .toc-rail {
    border-top: 1px solid var(--line);
  }
  .published-main { padding: 24px 16px 40px; }
  .markdown-body { padding: 20px; }
}
""".strip()

    def _library_index_html(self, books: list[dict[str, Any]]) -> str:
        cards = []
        for book in books:
            published_url = str(book.get("published_url") or f"/kb/books/{book['slug']}/")
            cards.append(
                f"""
                <article class="card">
                  <p class="eyebrow">Document</p>
                  <h2>{html.escape(str(book["title"]))}</h2>
                  <p>{html.escape(str(book.get("summary", "")))}</p>
                  <p class="meta">最后发布 {html.escape(str(book.get("last_publish_at") or "未发布"))}</p>
                  <a href="{published_url}">进入正式站</a>
                </article>
                """
            )
        cards_html = "\n".join(cards) or "<p>暂时还没有已发布文档。</p>"
        return f"""<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Benfast 文档发布中心</title>
    <link rel="stylesheet" href="/kb/books/assets/book.css" />
  </head>
  <body>
    <main class="content">
      <p class="eyebrow">Benfast Published Documents</p>
      <h1>实验室正式文档站</h1>
      <p class="summary">这里汇总已经从协作区发布完成的文档内容。</p>
      <p><a class="workspace-link" href="/workspace/">返回协作工作台</a></p>
      <section style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px;">
        {cards_html}
      </section>
    </main>
  </body>
</html>
"""

    def _write_publish_file(
        self,
        book_slug: str,
        relative_path: str,
        content: str,
    ) -> None:
        file_path = self.publish_root / book_slug / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        self.storage.write_text(self._published_storage_key(book_slug, relative_path), content)

    def _refresh_library_index(self, catalog: dict[str, Any]) -> None:
        published_books = [
            dict(book) for book in catalog["books"] if str(book.get("published_url") or "").strip()
        ]
        published_books.sort(key=lambda item: str(item.get("last_publish_at", "")), reverse=True)

        assets_dir = self.publish_root / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        styles = self._published_styles()
        (assets_dir / "book.css").write_text(styles, encoding="utf-8")
        self.storage.write_text("published/assets/book.css", styles)
        index_html = self._library_index_html(published_books)
        (self.publish_root / "index.html").write_text(index_html, encoding="utf-8")
        self.storage.write_text("published/index.html", index_html)
        catalog_json = json.dumps(
            published_books,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        (self.publish_root / "catalog.json").write_text(
            catalog_json,
            encoding="utf-8",
        )
        self.storage.write_text("published/catalog.json", catalog_json)

    def publish_book(
        self,
        book_id: str,
        *,
        message: str,
        user_id: int,
        username: str,
    ) -> dict[str, Any]:
        catalog = self._load_catalog()
        book = self._book_or_raise(book_id, catalog=catalog)
        full_tree = self._tree_for_book(book_id, catalog=catalog)
        ordered_pages = self._flatten_reading_order(book=book, full_tree=full_tree)
        if not ordered_pages:
            raise ValueError("文档至少需要一个页面才能发布")

        release_id = datetime.now(UTC).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
        publish_record = {
            "id": release_id,
            "message": message.strip() or "publish book",
            "page_count": len(ordered_pages),
            "published_at": self._now_iso(),
            "published_by": user_id,
            "published_by_name": username,
            "published_url": f"/kb/books/{book['slug']}/",
        }
        publishes = self.storage.read_json(self._publishes_key(book_id), [])
        if not isinstance(publishes, list):
            publishes = []
        next_publishes = [*publishes, publish_record]

        next_book = dict(book)
        next_book["last_publish_at"] = publish_record["published_at"]
        next_book["last_publish_release_id"] = release_id
        next_book["published_url"] = publish_record["published_url"]
        next_book["updated_at"] = publish_record["published_at"]
        next_book["updated_by"] = user_id
        next_book["updated_by_name"] = username

        next_catalog = {
            "books": [
                next_book if str(item.get("id")) == book_id else dict(item)
                for item in catalog["books"]
            ],
            "pages": catalog["pages"],
        }
        self._rebuild_unified_docs_site(next_catalog)

        self.storage.write_json(self._publishes_key(book_id), next_publishes)
        self._save_catalog(next_catalog)
        self.storage.write_json(self._book_key(book_id), next_book)
        return publish_record

    def list_publishes(self, book_id: str) -> list[dict[str, Any]]:
        self._book_or_raise(book_id)
        publishes = self.storage.read_json(self._publishes_key(book_id), [])
        if not isinstance(publishes, list):
            return []
        publishes.sort(key=lambda item: str(item.get("published_at", "")), reverse=True)
        return publishes

    def rebuild_site(self) -> dict[str, Any]:
        catalog = self._load_catalog()
        self._rebuild_unified_docs_site(catalog)
        books = self._site_books(catalog)
        return {
            "published_books": len(books),
            "docs_site_dir": str(self.docs_site_dir),
            "docs_source_root": str(self.docs_source_root),
        }


labdocs_service = LabDocsService()
