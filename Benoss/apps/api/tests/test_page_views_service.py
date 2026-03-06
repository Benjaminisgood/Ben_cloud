from __future__ import annotations

import sys
from pathlib import Path

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import User
from benoss_api.services import page_views


def _user(role: str = "user") -> User:
    return User(username="alice", role=role, is_active=True)


def test_login_page_context() -> None:
    ctx = page_views.login_page_context("/board")
    assert ctx["page"] == "login"
    assert ctx["next_url"] == "/board"


def test_can_access_admin() -> None:
    assert page_views.can_access_admin(_user(role="admin"))
    assert not page_views.can_access_admin(_user(role="user"))


def test_board_page_context_uses_valid_timezone(monkeypatch) -> None:
    monkeypatch.setattr(page_views, "get_setting_str", lambda *args, **kwargs: "UTC")
    ctx = page_views.board_page_context(_user())
    assert ctx["digest_timezone"] == "UTC"
    assert len(ctx["board_digest_day"]) == 10


def test_board_page_context_fallback_timezone(monkeypatch) -> None:
    monkeypatch.setattr(page_views, "get_setting_str", lambda *args, **kwargs: "Invalid/TZ")
    ctx = page_views.board_page_context(_user())
    assert ctx["digest_timezone"] == "UTC"

