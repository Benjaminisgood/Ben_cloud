from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.api.routes.records_feed import get_record
from benoss_api.models import Base, Comment, Content, Record, User


def _make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _seed_record_with_comment(db: Session) -> tuple[User, int]:
    author = User(username="alice", role="user", is_active=True)
    viewer = User(username="bob", role="user", is_active=True)
    author.set_password("123456")
    viewer.set_password("123456")
    content = Content(kind="text", file_type="text", text_content="hello", filename="text.txt", content_type="text/plain")
    db.add_all([author, viewer, content])
    db.flush()

    record = Record(user_id=author.id, content_id=content.id, visibility="public", preview="hello")
    db.add(record)
    db.flush()

    comment = Comment(record_id=record.id, user_id=viewer.id, body="nice")
    db.add(comment)
    db.commit()
    db.refresh(viewer)
    db.refresh(record)
    return viewer, record.id


def test_get_record_include_comments() -> None:
    db = _make_db()
    viewer, record_id = _seed_record_with_comment(db)

    out = get_record(record_id=record_id, include_comments=True, user=viewer, db=db)

    assert out["id"] == record_id
    assert "comments" in out
    assert len(out["comments"]) == 1
    assert out["comments"][0]["body"] == "nice"


def test_get_record_excludes_comments_by_default() -> None:
    db = _make_db()
    viewer, record_id = _seed_record_with_comment(db)

    out = get_record(record_id=record_id, include_comments=False, user=viewer, db=db)

    assert out["id"] == record_id
    assert "comments" not in out
