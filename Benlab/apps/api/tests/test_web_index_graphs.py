from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.db.base import Base
from benlab_api.db.session import get_db
from benlab_api.main import app
from benlab_api.models import Event, EventParticipant, Item, Location, Member
from benlab_api.web.deps import get_current_user


def _make_db() -> Session:
    engine = create_engine(
        "sqlite+pysqlite://",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)()


def _override_db(db: Session):
    def _dep():
        try:
            yield db
        finally:
            pass

    return _dep


def _member(member_id: int, username: str, name: str) -> Member:
    return Member(id=member_id, username=username, name=name, password_hash="x")


def test_index_graph_modes_present_and_slogans_removed() -> None:
    db = _make_db()
    alice = _member(1, "alice", "Alice")
    bob = _member(2, "bob", "Bob")
    item = Item(id=10, name="Camera", category="设备")
    location = Location(id=20, name="Lab")
    event = Event(id=30, title="Demo", owner_id=alice.id, start_time=datetime(2026, 3, 8, 12, 0))
    item.responsible_members.append(alice)
    item.locations.append(location)
    location.responsible_members.append(alice)
    event.participant_links.append(EventParticipant(member_id=bob.id, member=bob, role="guest"))
    event.items.append(item)
    event.locations.append(location)
    db.add_all([alice, bob, item, location, event])
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: alice

    try:
        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200
        body = response.text
        assert "简单图" in body
        assert "复杂图" in body
        assert "节点筛选" in body
        assert "关系筛选" in body
        assert "欢迎加入五天八小时社区" not in body
        assert "该下班下班" not in body
    finally:
        app.dependency_overrides.clear()
        db.close()
