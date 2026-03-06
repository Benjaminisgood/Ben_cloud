from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from ..core.config import get_settings


def new_operation_id() -> str:
    return uuid4().hex


def _rotate_audit_log_if_needed(path: Path, *, max_bytes: int) -> None:
    if max_bytes <= 0:
        return
    if not path.exists():
        return
    if path.stat().st_size < max_bytes:
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rotated_name = f"{path.stem}.{stamp}.{uuid4().hex[:8]}{path.suffix}"
    path.rename(path.with_name(rotated_name))


def write_audit_log(
    *,
    action: str,
    user: str,
    role: str,
    ip: str,
    target: str,
    ok: bool,
    request_id: str | None = None,
    operation_id: str | None = None,
    extra: dict[str, Any] | None = None,
) -> None:
    settings = get_settings()
    record = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "user": user,
        "role": role,
        "ip": ip,
        "target": target,
        "ok": ok,
    }
    if request_id:
        record["request_id"] = request_id
    if operation_id:
        record["operation_id"] = operation_id
    if extra:
        record["extra"] = extra

    settings.audit_log_path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_audit_log_if_needed(settings.audit_log_path, max_bytes=settings.audit_max_bytes)
    with settings.audit_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
