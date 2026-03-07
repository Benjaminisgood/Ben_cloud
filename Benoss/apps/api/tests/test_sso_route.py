from __future__ import annotations

import base64
import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.web.routes import sso


def _make_token(secret: str, username: str = "alice", role: str = "admin") -> str:
    payload = {"u": username, "r": role, "e": int(time.time()) + 30, "n": "nonce"}
    data = json.dumps(payload, separators=(",", ":"))
    sig = hmac.new(secret.encode(), data.encode(), hashlib.sha256).hexdigest()
    return base64.urlsafe_b64encode(f"{data}.{sig}".encode()).decode()


def test_verify_token_uses_loaded_settings_secret(monkeypatch) -> None:
    monkeypatch.setenv("SSO_SECRET", "wrong-runtime-secret")
    monkeypatch.setattr(sso, "get_settings", lambda: SimpleNamespace(SSO_SECRET="shared-secret"))

    token = _make_token("shared-secret")

    payload = sso._verify_token(token)

    assert payload is not None
    assert payload["u"] == "alice"
    assert payload["r"] == "admin"
