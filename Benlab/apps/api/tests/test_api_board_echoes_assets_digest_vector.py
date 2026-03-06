from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.api.deps import require_api_admin, require_api_user
from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.session import get_db
from benlab_api.main import app
from benlab_api.models import Attachment, Event, Item, Location, Member, Message


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


def test_board_echoes_assets_routes() -> None:
    db = _make_db()
    alice = _member(1, "alice", "Alice")
    bob = _member(2, "bob", "Bob")
    db.add_all([alice, bob])
    db.flush()

    item = Item(name="Item1")
    db.add(item)
    db.flush()

    attachment = Attachment(
        id=700,
        item_id=item.id,
        filename="asset-api.txt",
        created_at=datetime(2026, 2, 27, 9, 30, 0),
    )
    db.add(attachment)

    msg1 = Message(sender_id=alice.id, receiver_id=bob.id, content="hello #FastAPI", timestamp=datetime(2026, 2, 27, 9, 0, 0))
    msg2 = Message(sender_id=bob.id, receiver_id=alice.id, content="reply #Python", timestamp=datetime(2026, 2, 27, 10, 0, 0))
    msg3 = Message(sender_id=bob.id, receiver_id=bob.id, content="hidden #Secret", timestamp=datetime(2026, 2, 27, 11, 0, 0))
    db.add_all([msg1, msg2, msg3])
    db.commit()

    settings = get_settings()
    settings.ensure_data_dirs()
    path = settings.ATTACHMENTS_DIR / attachment.filename
    path.write_text("asset body", encoding="utf-8")

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: alice

    try:
        client = TestClient(app)

        board = client.get("/api/board", params={"days": 7})
        assert board.status_code == 200
        board_payload = board.json()
        assert len(board_payload["dates"]) == 7
        assert any(row["id"] == alice.id for row in board_payload["users"])
        assert any((row["name"] or "").lower() == "fastapi" for row in board_payload["top_tags"])

        board_cell = client.get("/api/board/cell", params={"day": "2026-02-27", "uid": bob.id})
        assert board_cell.status_code == 200
        assert len(board_cell.json()["items"]) == 1

        board_user_records = client.get(f"/api/board/user/{bob.id}/records")
        assert board_user_records.status_code == 200
        assert len(board_user_records.json()["items"]) == 1

        board_day_records = client.get("/api/board/date/2026-02-27")
        assert board_day_records.status_code == 200
        assert len(board_day_records.json()["items"]) == 2

        echoes = client.get("/api/echoes")
        assert echoes.status_code == 200
        echoes_payload = echoes.json()
        assert len(echoes_payload["records"]) == 2
        assert len(echoes_payload["assets"]) == 1

        invalid_echoes = client.get("/api/echoes", params={"file_type": "invalid"})
        assert invalid_echoes.status_code == 400

        assets = client.get("/api/generated-assets")
        assert assets.status_code == 200
        assert assets.json()["items"][0]["id"] == attachment.id

        asset_detail = client.get(f"/api/generated-assets/{attachment.id}")
        assert asset_detail.status_code == 200
        assert asset_detail.json()["id"] == attachment.id

        asset_blob = client.get(f"/api/generated-assets/{attachment.id}/blob")
        assert asset_blob.status_code == 200
        assert asset_blob.text == "asset body"
    finally:
        app.dependency_overrides.clear()
        path.unlink(missing_ok=True)
        db.close()


def test_digest_jobs_and_vector_routes() -> None:
    db = _make_db()
    admin = _member(1, get_settings().ADMIN_USERNAME, "Admin")
    alice = _member(2, "alice", "Alice")
    db.add_all([admin, alice])
    db.flush()

    item = Item(name="Vector item", notes="contains hello keyword")
    location = Location(name="Lab", notes="vector hello location")
    event = Event(title="Hello event", description="event hello", owner_id=admin.id)
    db.add_all([item, location, event])
    db.flush()

    msg = Message(sender_id=admin.id, receiver_id=alice.id, content="hello from record", timestamp=datetime(2026, 2, 27, 8, 0, 0))
    attachment = Attachment(id=701, item_id=item.id, filename="digest-2026-02-27.txt", created_at=datetime(2026, 2, 27, 12, 0, 0))
    db.add_all([msg, attachment])
    db.commit()

    settings = get_settings()
    settings.ensure_data_dirs()
    path = settings.ATTACHMENTS_DIR / attachment.filename
    path.write_text("digest content", encoding="utf-8")

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: admin
    app.dependency_overrides[require_api_admin] = lambda: admin

    try:
        client = TestClient(app)

        digest_refresh = client.post("/api/digest/daily", json={"day": "2026-02-27", "timezone": "Asia/Shanghai"})
        assert digest_refresh.status_code == 200
        assert digest_refresh.json()["day"] == "2026-02-27"

        jobs = client.get("/api/digest/jobs")
        assert jobs.status_code == 200
        assert len(jobs.json()["items"]) >= 1

        job = client.get("/api/digest/jobs/2026-02-27", params={"timezone": "Asia/Shanghai"})
        assert job.status_code == 200
        assert job.json()["day"] == "2026-02-27"

        vector_meta = client.get("/api/vector/meta")
        assert vector_meta.status_code == 200
        assert vector_meta.json()["backend"] == "keyword"

        vector_chat = client.post("/api/vector/chat", json={"query": "hello", "top_k": 5})
        assert vector_chat.status_code == 200
        assert vector_chat.json()["query"] == "hello"
        assert len(vector_chat.json()["results"]) >= 1

        vector_chat_bad = client.post("/api/vector/chat", json={"query": ""})
        assert vector_chat_bad.status_code == 400

        vector_rebuild = client.post("/api/vector/rebuild", json={"force": True})
        assert vector_rebuild.status_code == 200
        assert vector_rebuild.json()["ok"] is True
    finally:
        app.dependency_overrides.clear()
        path.unlink(missing_ok=True)
        db.close()
