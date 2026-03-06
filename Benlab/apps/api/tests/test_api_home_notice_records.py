from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.api.deps import require_api_user
from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.session import get_db
from benlab_api.main import app
from benlab_api.models import Attachment, Item, Member, Message
from benlab_api.repositories.records_api_repo import set_record_visibility


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


def test_home_notice_records_endpoints() -> None:
    db = _make_db()
    alice = _member(1, "alice", "Alice")
    bob = _member(2, "bob", "Bob")
    db.add_all([alice, bob])
    db.flush()

    msg1 = Message(sender_id=alice.id, receiver_id=bob.id, content="hello #FastAPI", timestamp=datetime(2026, 2, 27, 9, 0, 0))
    msg2 = Message(sender_id=bob.id, receiver_id=alice.id, content="reply #Python", timestamp=datetime(2026, 2, 27, 10, 0, 0))
    db.add_all([msg1, msg2])
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: alice

    try:
        client = TestClient(app)

        home = client.get("/api/home/today")
        assert home.status_code == 200
        assert "metrics" in home.json()

        notice_records = client.get("/api/notice/records", params={"limit": 1})
        assert notice_records.status_code == 200
        assert notice_records.json()["has_more"] is True
        assert len(notice_records.json()["items"]) == 1

        notice_render = client.get("/api/notice/render")
        assert notice_render.status_code == 200
        assert "notice-record-" in notice_render.json()["rendered_html"]

        records = client.get("/api/records")
        assert records.status_code == 200
        assert len(records.json()["items"]) == 2

        pull = client.get("/api/pull")
        assert pull.status_code == 200
        assert len(pull.json()["items"]) == 2

        detail = client.get(f"/api/records/{msg1.id}")
        assert detail.status_code == 200
        assert detail.json()["id"] == msg1.id

        tags = client.get("/api/tags", params={"q": "fast"})
        assert tags.status_code == 200
        assert tags.json()["items"][0]["name"].lower() == "fastapi"

        blob = client.get(f"/api/contents/{msg1.id}/blob")
        assert blob.status_code == 200
        assert blob.text.startswith("hello")

        created_comment = client.post(f"/api/records/{msg1.id}/comments", json={"body": "nice"})
        assert created_comment.status_code == 201
        assert created_comment.json()["body"] == "nice"

        comments = client.get(f"/api/records/{msg1.id}/comments")
        assert comments.status_code == 200
        assert comments.json()["items"][0]["body"] == "nice"
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_record_mutations_and_visibility() -> None:
    db = _make_db()
    alice = _member(1, "alice", "Alice")
    bob = _member(2, "bob", "Bob")
    db.add_all([alice, bob])
    db.flush()

    hidden = Message(sender_id=bob.id, receiver_id=bob.id, content="hidden #Ops", timestamp=datetime(2026, 2, 27, 11, 0, 0))
    public_msg = Message(sender_id=bob.id, receiver_id=bob.id, content="public #Ops", timestamp=datetime(2026, 2, 27, 11, 5, 0))
    db.add_all([hidden, public_msg])
    db.commit()
    set_record_visibility(db, record_id=public_msg.id, visibility="public", user_id=bob.id)

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: alice

    try:
        client = TestClient(app)

        hidden_detail = client.get(f"/api/records/{hidden.id}")
        assert hidden_detail.status_code == 404

        public_detail = client.get(f"/api/records/{public_msg.id}")
        assert public_detail.status_code == 200
        assert public_detail.json()["visibility"] == "public"

        public_only_list = client.get("/api/records", params={"visibility": "public"})
        assert public_only_list.status_code == 200
        assert any(item["id"] == public_msg.id for item in public_only_list.json()["items"])

        created = client.post(
            "/api/records",
            json={"text": "new post", "tags": "fastapi,python", "receiver_id": bob.id, "visibility": "public"},
        )
        assert created.status_code == 201
        created_id = created.json()["id"]
        assert created.json()["visibility"] == "public"
        assert created.json()["can_edit"] is True

        updated = client.patch(f"/api/records/{created_id}", json={"text": "updated post", "tags": "newtag", "visibility": "private"})
        assert updated.status_code == 200
        assert updated.json()["visibility"] == "private"
        assert "updated post" in updated.json()["content"]["text"]

        deleted = client.delete(f"/api/records/{created_id}")
        assert deleted.status_code == 204

        deleted_detail = client.get(f"/api/records/{created_id}")
        assert deleted_detail.status_code == 404
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_records_direct_upload_and_attachment_blob() -> None:
    db = _make_db()
    alice = _member(1, "alice", "Alice")
    db.add(alice)
    db.flush()

    item = Item(name="i1")
    db.add(item)
    db.flush()

    attachment = Attachment(id=901, item_id=item.id, filename="api-test-blob.txt")
    db.add(attachment)
    db.commit()

    settings = get_settings()
    settings.ensure_data_dirs()
    path = settings.ATTACHMENTS_DIR / attachment.filename
    path.write_text("blob-from-attachment", encoding="utf-8")

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[require_api_user] = lambda: alice

    try:
        client = TestClient(app)

        token_resp = client.get(
            "/api/direct-upload/token",
            params={"filename": "a.txt", "content_type": "text/plain", "size_bytes": 1},
        )
        assert token_resp.status_code == 200
        token = token_resp.json()["token"]

        confirm_resp = client.post(
            "/api/direct-upload/confirm",
            json={"token": token, "visibility": "public", "tags": "upload"},
        )
        assert confirm_resp.status_code == 201
        assert confirm_resp.json()["visibility"] == "public"

        blob = client.get(f"/api/contents/{attachment.id}/blob")
        assert blob.status_code == 200
        assert blob.text == "blob-from-attachment"
    finally:
        app.dependency_overrides.clear()
        path.unlink(missing_ok=True)
        db.close()
