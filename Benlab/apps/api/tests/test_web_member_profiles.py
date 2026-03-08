from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from benlab_api.core.config import get_settings
from benlab_api.db.base import Base
from benlab_api.db.session import get_db
from benlab_api.main import app
from benlab_api.models import Event, Item, Location, Member, MemberConnection
from benlab_api.services.member_profiles import serialize_profile_notes
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


def test_admin_profile_page_shows_private_dossier_and_relations() -> None:
    admin_username = get_settings().ADMIN_USERNAME
    db = _make_db()
    admin = _member(1, admin_username, "Admin")
    bob = _member(2, "bob", "Bob")
    charlie = _member(3, "charlie", "Charlie")
    bob.notes = serialize_profile_notes(
        {
            "nickname": "阿博",
            "gender": "male",
            "birthday": "1994-06-18",
            "birthyear": 1994,
            "relationship_label": "大学同学",
            "first_met": {
                "date": "2012-09-01",
                "location": "宿舍楼",
                "feeling": "很能聊",
                "story": "报到第一天遇到",
            },
            "location_relations": [{"location_id": 10, "relation": "live", "note": "一起住过"}],
            "item_relations": [{"item_id": 20, "relation": "favorite", "note": "一起买的"}],
            "event_relations": [{"event_id": 30, "relation": "join", "note": "一起参加"}],
        }
    )
    location = Location(id=10, name="上海")
    item = Item(id=20, name="相机")
    event = Event(id=30, title="毕业旅行", owner_id=admin.id)
    connection = MemberConnection(
        source_member_id=bob.id,
        target_member_id=charlie.id,
        relation_type="friend",
        closeness=4,
        note="常联系",
    )
    db.add_all([admin, bob, charlie, location, item, event, connection])
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/member/2")
        assert response.status_code == 200
        body = response.text
        assert "大学同学" in body
        assert "宿舍楼" in body
        assert "报到第一天遇到" in body
        assert "上海" in body
        assert "相机" in body
        assert "毕业旅行" in body
        assert "一起买的" in body
        assert "Charlie" in body
        assert "常联系" in body
    finally:
        app.dependency_overrides.clear()
        db.close()


def test_admin_can_open_other_member_edit_page() -> None:
    admin_username = get_settings().ADMIN_USERNAME
    db = _make_db()
    admin = _member(1, admin_username, "Admin")
    bob = _member(2, "bob", "Bob")
    db.add_all([admin, bob])
    db.commit()

    app.dependency_overrides[get_db] = _override_db(db)
    app.dependency_overrides[get_current_user] = lambda: admin

    try:
        client = TestClient(app)
        response = client.get("/member/2/edit")
        assert response.status_code == 200
        body = response.text
        assert "管理员关系档案" in body
        assert 'name="relationship_label"' in body
        assert 'name="first_met_story"' in body
    finally:
        app.dependency_overrides.clear()
        db.close()
