"""SSO token verification utilities for Benbot integration."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time


def verify_sso_token(sso_secret: str, token: str) -> dict | None:
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        dot_pos = decoded.rfind(".")
        if dot_pos == -1:
            return None
        data, sig = decoded[:dot_pos], decoded[dot_pos + 1 :]
        expected = hmac.new(sso_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data)
        if payload.get("e", 0) < time.time():
            return None
        return payload
    except Exception:
        return None
