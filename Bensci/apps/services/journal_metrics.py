from __future__ import annotations

import csv
import re
from pathlib import Path

from apps.core.config import settings

_CACHE_KEY: tuple[str, float] | None = None
_CACHE_VALUE: dict[str, float] = {}


def normalize_journal_name(name: str) -> str:
    text = (name or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _detect_columns(fieldnames: list[str] | None) -> tuple[str | None, str | None]:
    if not fieldnames:
        return None, None

    lowered = {name.lower().strip(): name for name in fieldnames}

    journal_candidates = ["journal", "journal_name", "title", "source_title"]
    impact_candidates = ["impact_factor", "if", "jif", "impact"]

    journal_col = next((lowered[key] for key in journal_candidates if key in lowered), None)
    impact_col = next((lowered[key] for key in impact_candidates if key in lowered), None)
    return journal_col, impact_col


def load_journal_impact_factors() -> dict[str, float]:
    global _CACHE_KEY, _CACHE_VALUE

    path = settings.journal_metrics_csv_path
    if path is None:
        return {}

    csv_path = Path(path)
    if not csv_path.exists():
        return {}

    stat = csv_path.stat()
    cache_key = (str(csv_path.resolve()), stat.st_mtime)
    if _CACHE_KEY == cache_key:
        return _CACHE_VALUE

    metrics: dict[str, float] = {}
    with csv_path.open("r", encoding="utf-8", newline="") as fp:
        reader = csv.DictReader(fp)
        journal_col, impact_col = _detect_columns(reader.fieldnames)
        if journal_col is None or impact_col is None:
            _CACHE_KEY = cache_key
            _CACHE_VALUE = {}
            return {}

        for row in reader:
            journal = normalize_journal_name(str(row.get(journal_col) or ""))
            if not journal:
                continue
            impact_raw = str(row.get(impact_col) or "").strip()
            if not impact_raw:
                continue
            try:
                metrics[journal] = float(impact_raw)
            except ValueError:
                continue

    _CACHE_KEY = cache_key
    _CACHE_VALUE = metrics
    return metrics


def lookup_impact_factor(journal: str) -> float | None:
    metrics = load_journal_impact_factors()
    if not metrics:
        return None

    normalized = normalize_journal_name(journal)
    if not normalized:
        return None

    direct = metrics.get(normalized)
    if direct is not None:
        return direct

    for candidate, impact in metrics.items():
        if normalized == candidate:
            return impact
        if normalized in candidate or candidate in normalized:
            return impact
    return None
