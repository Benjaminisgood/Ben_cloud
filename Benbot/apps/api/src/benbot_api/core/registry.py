from __future__ import annotations

import logging
from pathlib import Path

import yaml

from .config import Settings

logger = logging.getLogger(__name__)


def validate_registry_alignment(settings: Settings) -> None:
    registry_path = Path(settings.PROJECT_REGISTRY_FILE)
    if not registry_path.exists():
        logger.warning("Project registry not found: %s", registry_path)
        return

    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        if settings.PROJECT_REGISTRY_STRICT:
            raise RuntimeError(f"Failed to parse registry file: {registry_path}") from exc
        logger.warning("Failed to parse registry file %s: %s", registry_path, exc)
        return

    app_ids = {
        str(item.get("id", "")).strip()
        for item in payload.get("apps", [])
        if isinstance(item, dict)
    }
    benbot_project_ids = {project.id for project in settings.get_projects()}
    missing_in_registry = sorted(benbot_project_ids - app_ids)
    missing_in_benbot = sorted(app_ids - benbot_project_ids - {"benbot"})

    if not missing_in_registry and not missing_in_benbot:
        return

    details = []
    if missing_in_registry:
        details.append(f"missing_in_registry={missing_in_registry}")
    if missing_in_benbot:
        details.append(f"missing_in_benbot={missing_in_benbot}")
    message = "Project registry mismatch: " + ", ".join(details)
    if settings.PROJECT_REGISTRY_STRICT:
        raise RuntimeError(message)
    logger.warning(message)
