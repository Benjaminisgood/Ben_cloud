from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import PurePosixPath

_SAFE_FILE_STEM_RE = re.compile(r"[^A-Za-z0-9_\-.\u4e00-\u9fff]+")
_MAX_STEM_LENGTH = 80


@dataclass(frozen=True)
class ExportArtifact:
    filename: str
    media_type: str
    content: bytes


def _normalize_file_stem(raw_name: str | None) -> str:
    candidate = (raw_name or "").strip()
    if not candidate:
        return "note"

    candidate = candidate.replace("\\", "/")
    candidate = PurePosixPath(candidate).name
    if candidate.lower().endswith(".md"):
        candidate = candidate[:-3]

    candidate = _SAFE_FILE_STEM_RE.sub("_", candidate).strip("._-")
    if not candidate:
        return "note"

    return candidate[:_MAX_STEM_LENGTH]


def markdown_to_plain_text(content: str) -> str:
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"!\[([^\]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}\d+\.\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}>\s?", "", text, flags=re.MULTILINE)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = text.replace("**", "").replace("__", "").replace("*", "").replace("_", "")
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text + ("\n" if text else "")


def _markdown_to_html_body(content: str) -> str:
    try:
        import markdown as markdown_lib  # type: ignore

        return markdown_lib.markdown(
            content,
            extensions=["fenced_code", "tables", "sane_lists"],
        )
    except Exception:
        escaped = html.escape(content)
        return f"<pre>{escaped}</pre>"


def markdown_to_html_document(content: str, *, title: str) -> str:
    body = _markdown_to_html_body(content)
    safe_title = html.escape(title)
    return (
        "<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>"
        f"<title>{safe_title}</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        "<style>"
        "body{font-family:'PingFang SC','Microsoft YaHei',sans-serif;margin:32px;line-height:1.7;color:#111827;}"
        "pre{background:#f3f4f6;padding:12px;border-radius:8px;overflow:auto;}"
        "code{background:#f3f4f6;padding:2px 4px;border-radius:4px;}"
        "table{border-collapse:collapse;width:100%;}th,td{border:1px solid #e5e7eb;padding:6px 8px;}"
        "th{background:#f9fafb;}img{max-width:100%;}"
        "</style></head><body>"
        f"{body}</body></html>"
    )


def build_export_artifact(*, export_format: str, content: str, file_name: str | None = None) -> ExportArtifact:
    stem = _normalize_file_stem(file_name)

    if export_format == "md":
        return ExportArtifact(
            filename=f"{stem}.md",
            media_type="text/markdown; charset=utf-8",
            content=content.encode("utf-8"),
        )
    if export_format == "txt":
        plain_text = markdown_to_plain_text(content)
        return ExportArtifact(
            filename=f"{stem}.txt",
            media_type="text/plain; charset=utf-8",
            content=plain_text.encode("utf-8"),
        )
    if export_format == "html":
        html_doc = markdown_to_html_document(content, title=stem)
        return ExportArtifact(
            filename=f"{stem}.html",
            media_type="text/html; charset=utf-8",
            content=html_doc.encode("utf-8"),
        )

    raise ValueError("unsupported_export_format")
