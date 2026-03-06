from __future__ import annotations

import sys
from pathlib import Path

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.services.records_service import auto_tags, normalize_visibility, parse_tags, preview_text


def test_parse_tags_deduplicate_and_limit() -> None:
    raw = [" Alpha ", "alpha", "Beta"] + [f"Tag{i}" for i in range(30)]
    tags = parse_tags(raw)
    assert tags[0] == "Alpha"
    assert "alpha" not in tags[1:]
    assert len(tags) == 20


def test_auto_tags_extracts_hash_words() -> None:
    text = "今天完成 #FastAPI 集成，顺便看了 #python 和 #Python。"
    tags = auto_tags(text)
    assert "FastAPI" in tags
    assert any(t.lower() == "python" for t in tags)
    assert len([t for t in tags if t.lower() == "python"]) == 1


def test_normalize_visibility_fallback() -> None:
    assert normalize_visibility("public") == "public"
    assert normalize_visibility("PRIVATE") == "private"
    assert normalize_visibility("unknown", default="public") == "public"


def test_preview_text_truncates() -> None:
    text = "x" * 30
    out = preview_text(text, limit=10)
    assert len(out) == 10
    assert out.endswith("…")

