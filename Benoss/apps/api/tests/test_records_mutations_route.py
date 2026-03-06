from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.api.deps import require_api_user
from benoss_api.api.routes.records_mutations import router
from benoss_api.db.session import get_db
from benoss_api.models import Base, Content, Record, User


def _make_db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _make_client(db: Session, user: User) -> TestClient:
    app = FastAPI()
    app.include_router(router, prefix="/api")

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_api_user] = lambda: user
    return TestClient(app)


def _seed_text_record(db: Session) -> tuple[User, int]:
    user = User(username="alice", role="user", is_active=True, password_hash="x")
    db.add(user)
    db.flush()

    content = Content(
        kind="text",
        file_type="text",
        text_content="hello",
        oss_key="records/source/text.txt",
        filename="text.txt",
        content_type="text/plain; charset=utf-8",
        size_bytes=5,
        sha256="old-sha",
    )
    db.add(content)
    db.flush()

    record = Record(
        user_id=user.id,
        content_id=content.id,
        visibility="public",
        preview="hello",
    )
    db.add(record)
    db.commit()
    db.refresh(user)
    db.refresh(record)
    return user, record.id


def test_update_record_endpoint_accepts_form_data(monkeypatch) -> None:
    from benoss_api.services import records_commands

    monkeypatch.setattr(records_commands, "put_object_bytes", lambda *_args, **_kwargs: None)

    db = _make_db()
    user, record_id = _seed_text_record(db)
    client = _make_client(db, user)

    response = client.patch(
        f"/api/records/{record_id}",
        data={
            "text": "updated via form",
            "tags": "codex,patched",
            "visibility": "private",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["visibility"] == "private"
    assert payload["tags"] == ["codex", "patched"]
    assert payload["content"]["text"] == "updated via form"

    db.expire_all()
    updated = db.get(Record, record_id)
    assert updated is not None
    assert updated.visibility == "private"
    assert updated.preview == "updated via form"
    assert updated.content.text_content == "updated via form"


def test_update_record_endpoint_rejects_blank_text_form(monkeypatch) -> None:
    from benoss_api.services import records_commands

    monkeypatch.setattr(records_commands, "put_object_bytes", lambda *_args, **_kwargs: None)

    db = _make_db()
    user, record_id = _seed_text_record(db)
    client = _make_client(db, user)

    response = client.patch(
        f"/api/records/{record_id}",
        data={
            "text": "   ",
            "tags": "codex",
            "visibility": "public",
        },
    )

    assert response.status_code == 400
    assert response.json() == {"detail": "text is required"}

    db.expire_all()
    updated = db.get(Record, record_id)
    assert updated is not None
    assert updated.preview == "hello"
    assert updated.content.text_content == "hello"
