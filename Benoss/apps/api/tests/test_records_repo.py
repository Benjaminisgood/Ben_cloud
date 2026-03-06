from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Base, Content, Record, Tag, User
from benoss_api.repositories.records_repo import list_records, pull_records, search_tags


def _build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)()


def _seed_records(db: Session) -> tuple[User, User]:
    owner = User(username="owner", password_hash="x", role="user", is_active=True)
    peer = User(username="peer", password_hash="x", role="user", is_active=True)
    db.add_all([owner, peer])
    db.flush()

    content_private = Content(kind="text", file_type="text", text_content="private", filename="a.txt")
    content_public = Content(kind="text", file_type="text", text_content="public", filename="b.txt")
    db.add_all([content_private, content_public])
    db.flush()

    private_record = Record(
        user_id=owner.id,
        content_id=content_private.id,
        visibility="private",
        preview="private preview",
        created_at=datetime(2026, 2, 27, 8, 0, 0),
    )
    public_record = Record(
        user_id=peer.id,
        content_id=content_public.id,
        visibility="public",
        preview="public preview",
        created_at=datetime(2026, 2, 27, 9, 0, 0),
    )
    t_python = Tag(name="Python", name_norm="python")
    public_record.tags = [t_python]
    db.add_all([private_record, public_record, t_python])
    db.commit()
    return owner, peer


def test_list_records_visibility_and_day_filter() -> None:
    db = _build_session()
    owner, peer = _seed_records(db)

    owner_rows, _ = list_records(db, viewer_id=owner.id, day="2026-02-27", limit=10)
    assert len(owner_rows) == 2

    peer_rows, _ = list_records(db, viewer_id=peer.id, day="2026-02-27", limit=10)
    assert len(peer_rows) == 1
    assert peer_rows[0].visibility == "public"

    public_only_rows, _ = list_records(db, viewer_id=owner.id, visibility="public", limit=10)
    assert len(public_only_rows) == 1


def test_pull_records_and_tag_search() -> None:
    db = _build_session()
    owner, _ = _seed_records(db)

    pulled, _ = pull_records(db, viewer_id=owner.id, tag="python", limit=10)
    assert len(pulled) == 1
    assert pulled[0].visibility == "public"

    tags = search_tags(db, q="py", limit=10)
    assert [t.name for t in tags] == ["Python"]

