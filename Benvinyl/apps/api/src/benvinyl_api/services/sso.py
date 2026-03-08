from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any


def verify_sso_token(secret: str, token: str) -> dict[str, Any] | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        payload_raw, provided_sig = decoded.rsplit(".", 1)
    except Exception:
        return None

    expected_sig = hmac.new(secret.encode(), payload_raw.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig, provided_sig):
        return None

    try:
        payload = json.loads(payload_raw)
    except json.JSONDecodeError:
        return None

    if not isinstance(payload, dict):
        return None
    if int(payload.get("e", 0)) < int(time.time()):
        return None
    if not str(payload.get("n", "")).strip():
        return None
    return payload
