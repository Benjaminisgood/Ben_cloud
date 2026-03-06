"""File type detection utilities, extracted from the monolithic api.py."""
from __future__ import annotations

from pathlib import Path

_TEXT_FILE_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".rst", ".json", ".jsonl", ".yaml", ".yml",
    ".toml", ".ini", ".cfg", ".conf", ".csv", ".tsv", ".xml", ".html", ".htm",
    ".css", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".py", ".java",
    ".go", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc", ".sql", ".sh", ".bash",
    ".zsh", ".ps1", ".rb", ".php", ".swift", ".kt", ".kts", ".dart", ".vue",
    ".svelte", ".env", ".log",
}
_TEXT_FILE_MIME_TYPES = {
    "application/json", "application/ld+json", "application/xml",
    "application/yaml", "application/x-yaml", "application/toml",
    "application/x-toml", "application/javascript", "application/x-javascript",
    "application/sql", "application/csv", "application/x-sh",
    "application/x-httpd-php",
}
_WEB_FILE_EXTENSIONS = (".html", ".htm", ".xhtml")
_WEB_FILE_MIME_TYPES = {"text/html", "application/xhtml+xml"}
_IMAGE_FILE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".svg")
_VIDEO_FILE_EXTENSIONS = (".mp4", ".mov", ".webm", ".mkv", ".avi")
_AUDIO_FILE_EXTENSIONS = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")
_LOG_FILE_EXTENSIONS = (".log", ".out", ".err")
_DATABASE_FILE_EXTENSIONS = (".db", ".sqlite", ".sqlite3", ".db3")
_DATABASE_FILE_MIME_TYPES = {"application/x-sqlite3", "application/vnd.sqlite3"}
_ARCHIVE_FILE_EXTENSIONS = (
    ".zip", ".tar", ".gz", ".tgz", ".bz2", ".tbz", ".tbz2",
    ".xz", ".txz", ".7z", ".rar",
)
_ARCHIVE_FILE_MIME_TYPES = {
    "application/zip", "application/x-zip-compressed", "application/x-tar",
    "application/gzip", "application/x-gzip", "application/x-7z-compressed",
    "application/vnd.rar", "application/x-rar-compressed",
    "application/x-bzip2", "application/x-xz",
}
_DOCUMENT_FILE_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx",
    ".odt", ".ods", ".odp",
)
_DOCUMENT_FILE_MIME_TYPES = {
    "application/pdf", "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.oasis.opendocument.spreadsheet",
    "application/vnd.oasis.opendocument.presentation",
}

VALID_FILE_TYPES = {"text", "web", "image", "video", "audio", "log", "database", "archive", "document", "file"}


def detect_file_type(content_type: str | None, filename_or_ext: str | None) -> str:
    ctype = str(content_type or "").split(";", 1)[0].strip().lower()
    name = str(filename_or_ext or "").strip().lower()
    suffix = Path(name).suffix.lower() if name else ""

    if ctype.startswith("image/") or suffix in _IMAGE_FILE_EXTENSIONS:
        return "image"
    if ctype.startswith("video/") or suffix in _VIDEO_FILE_EXTENSIONS:
        return "video"
    if ctype.startswith("audio/") or suffix in _AUDIO_FILE_EXTENSIONS:
        return "audio"
    if (
        ctype in _WEB_FILE_MIME_TYPES
        or ctype.startswith("text/html")
        or ctype.startswith("application/xhtml+xml")
        or suffix in _WEB_FILE_EXTENSIONS
        or name.endswith(_WEB_FILE_EXTENSIONS)
    ):
        return "web"
    if suffix in _LOG_FILE_EXTENSIONS:
        return "log"
    if ctype in _DATABASE_FILE_MIME_TYPES or suffix in _DATABASE_FILE_EXTENSIONS:
        return "database"
    if ctype in _ARCHIVE_FILE_MIME_TYPES or suffix in _ARCHIVE_FILE_EXTENSIONS:
        return "archive"
    if ctype in _DOCUMENT_FILE_MIME_TYPES or suffix in _DOCUMENT_FILE_EXTENSIONS:
        return "document"
    if ctype.startswith("text/") or ctype in _TEXT_FILE_MIME_TYPES or suffix in _TEXT_FILE_EXTENSIONS:
        return "text"
    return "file"
