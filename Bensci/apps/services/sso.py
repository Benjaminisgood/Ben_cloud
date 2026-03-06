"""SSO token generation and verification for sub-project single sign-on."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

SSO_TOKEN_TTL = 30  # seconds; short-lived to prevent replay attacks


def create_sso_token(sso_secret: str, username: str, role: str) -> str:
    """Create a signed, short-lived SSO token for sub-project login."""
    payload = {
        "u": username,
        "r": role,
        "e": int(time.time()) + SSO_TOKEN_TTL,
        "n": secrets.token_hex(8),  # nonce prevents replay
    }
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(sso_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    raw = f"{data}.{sig}"
    return base64.urlsafe_b64encode(raw.encode()).decode()


def verify_sso_token(sso_secret: str, token: str) -> dict | None:
    """Verify a token; returns payload dict or None if invalid/expired."""
    try:
        decoded = base64.urlsafe_b64decode(token.encode()).decode()
        # rsplit on last '.' to split data from signature
        dot_pos = decoded.rfind(".")
        if dot_pos == -1:
            return None
        data, sig = decoded[:dot_pos], decoded[dot_pos + 1:]
        expected = hmac.new(sso_secret.encode(), data.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return None
        payload = json.loads(data)
        if payload.get("e", 0) < time.time():
            return None  # expired
        return payload
    except Exception:
        return None
