from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Base
from benoss_api.services.auth import authenticate_user, create_user, username_exists, validate_registration_input


def _make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def test_validate_registration_input() -> None:
    assert validate_registration_input("", "123456", "123456") == "用户名不能为空"
    assert validate_registration_input("ab", "123456", "123456") == "用户名长度需在 3-40 之间"
    assert validate_registration_input("alice", "123456", "1234567") == "两次输入的密码不一致"
    assert validate_registration_input("alice", "12345", "12345") == "密码至少 6 位"
    assert validate_registration_input("alice", "123456", "123456") is None


def test_create_user_and_authenticate() -> None:
    db = _make_db()
    create_user(db, username="alice", password="123456")
    user = authenticate_user(db, username="alice", password="123456")
    assert user is not None
    assert user.username == "alice"


def test_authenticate_user_rejects_wrong_password() -> None:
    db = _make_db()
    create_user(db, username="alice", password="123456")
    assert authenticate_user(db, username="alice", password="wrong-password") is None


def test_username_exists() -> None:
    db = _make_db()
    create_user(db, username="alice", password="123456")
    assert username_exists(db, username="alice")
    assert not username_exists(db, username="bob")

