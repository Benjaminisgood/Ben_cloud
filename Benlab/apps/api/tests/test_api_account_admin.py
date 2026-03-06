from __future__ import annotations

import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.api.deps import require_api_admin, require_api_user
from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.session import get_db
from benlab_api.main import app
from benlab_api.models import Member


def _make_db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)()


def _member(member_id: int, username: str, name: str) -> Member:
    return Member(id=member_id, username=username, name=name, password_hash="x")


def _override_db(db: Session):
    def _dep():
        try:
            yield db
        finally:
            pass

    return _dep


def test_account_and_users_api() -> None:
    admin_username = get_settings().ADMIN_USERNAME
    db = _make_db()
    admin = _member(1, admin_username, "Admin")
    bob = _member(2, "bob", "Bob")
    db.add_all([admin, bob])
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/api/account")
        assert response.status_code == 200
        payload = response.json()
        assert payload["current_user"]["username"] == admin_username
        assert payload["current_user"]["role"] == "admin"
        assert "description" in payload["current_user"]
        assert [row["username"] for row in payload["users"]] == sorted([admin_username, "bob"])

        update_desc = client.patch("/api/account/description", json={"description": "hello profile"})
        assert update_desc.status_code == 200
        assert update_desc.json() == {"description": "hello profile"}

        verify = client.get("/api/account")
        assert verify.status_code == 200
        assert verify.json()["current_user"]["description"] == "hello profile"

        too_long = client.patch("/api/account/description", json={"description": "x" * 501})
        assert too_long.status_code == 400

        users_response = client.get("/api/users")
        assert users_response.status_code == 200
        assert [row["username"] for row in users_response.json()["items"]] == sorted([admin_username, "bob"])
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_require_api_admin_rejects_non_admin() -> None:
    with pytest.raises(HTTPException) as exc:
        require_api_admin(_member(2, "bob", "Bob"))
    assert exc.value.status_code == 403


def test_require_api_admin_uses_env_admin_username(monkeypatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("ADMIN_USERNAME", "root")
    try:
        assert require_api_admin(_member(1, "root", "Root")).username == "root"
        with pytest.raises(HTTPException) as exc:
            require_api_admin(_member(2, "admin", "Admin"))
        assert exc.value.status_code == 403
    finally:
        get_settings.cache_clear()


def test_admin_settings_roundtrip_payload() -> None:
    admin_username = get_settings().ADMIN_USERNAME
    db = _make_db()
    admin = _member(1, admin_username, "Admin")
    db.add(admin)
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_admin] = lambda: admin

    with tempfile.TemporaryDirectory() as tmp_dir:
        settings_file = os.path.join(tmp_dir, "admin_settings.json")
        os.environ["BENLAB_ADMIN_SETTINGS_FILE"] = settings_file

        try:
            client = TestClient(app)
            response = client.get("/api/admin/settings")
            assert response.status_code == 200
            groups = response.json().get("groups", [])
            assert groups

            update_response = client.put(
                "/api/admin/settings",
                json={"values": {"BOARD_DEFAULT_DAYS": 12, "DIGEST_TIMEZONE": "UTC"}, "reset_keys": []},
            )
            assert update_response.status_code == 200

            updated = client.get("/api/admin/settings")
            assert updated.status_code == 200
            flat_items = [item for group in updated.json().get("groups", []) for item in group.get("items", [])]
            kv = {item["key"]: item["value"] for item in flat_items}
            assert kv["BOARD_DEFAULT_DAYS"] == "12"
            assert kv["DIGEST_TIMEZONE"] == "UTC"

            bad_update = client.put("/api/admin/settings", json={"values": {"UNKNOWN_KEY": 1}, "reset_keys": []})
            assert bad_update.status_code == 400
        finally:
            os.environ.pop("BENLAB_ADMIN_SETTINGS_FILE", None)
            app.dependency_overrides.clear()
            db.close()
