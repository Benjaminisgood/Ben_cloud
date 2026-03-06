from __future__ import annotations

import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

API_SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(API_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(API_SRC_DIR))

from benoss_api.models import Base, Content, Record, User
from benoss_api.services.records_commands import (
    RecordCommandError,
    clone_record,
    create_comment,
    create_record,
    issue_direct_upload_token,
    resolve_tags,
    update_record,
    validate_comment_body,
)


def _make_db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)()


def _user() -> User:
    return User(id=1, username="alice", role="user", is_active=True)


def test_resolve_tags_fallback_to_auto_tags() -> None:
    tags = resolve_tags("", "今天学习 #FastAPI 和 #Python")
    assert "FastAPI" in tags
    assert any(tag.lower() == "python" for tag in tags)


def test_validate_comment_body_errors() -> None:
    with pytest.raises(RecordCommandError):
        validate_comment_body("")
    with pytest.raises(RecordCommandError):
        validate_comment_body("x" * 2001)


def test_create_comment_success() -> None:
    db = _make_db()
    comment = create_comment(db, record_id=1, user_id=1, body="hello")
    assert comment.body == "hello"
    assert comment.record_id == 1


def test_create_record_requires_text_or_file() -> None:
    db = _make_db()
    with pytest.raises(RecordCommandError):
        create_record(db, user=_user(), text_value="", visibility="public", raw_tags="", upload_file=None)


def test_issue_direct_upload_requires_remote_backend(monkeypatch) -> None:
    from benoss_api.services import records_commands

    monkeypatch.setattr(records_commands, "has_remote_backend", lambda: False)
    with pytest.raises(RecordCommandError):
        issue_direct_upload_token(user=_user(), filename="a.txt", content_type="text/plain", size_bytes=1, sha256="")


def test_clone_record_creates_new_record_for_viewer(monkeypatch) -> None:
    from benoss_api.services import records_commands

    db = _make_db()
    owner = User(username="owner", role="user", is_active=True, password_hash="x")
    viewer = User(username="viewer", role="user", is_active=True, password_hash="x")
    db.add_all([owner, viewer])
    db.flush()

    content = Content(
        kind="file",
        file_type="file",
        text_content="",
        oss_key="records/source/doc.txt",
        filename="doc.txt",
        content_type="text/plain",
        size_bytes=3,
        sha256="abc",
    )
    db.add(content)
    db.flush()

    source = Record(
        user_id=owner.id,
        content_id=content.id,
        visibility="public",
        preview="src preview",
    )
    source.set_tags(["tag1", "tag2"], db=db)
    db.add(source)
    db.commit()
    db.refresh(source)

    monkeypatch.setattr(records_commands, "copy_object", lambda _src, _dst: None)

    cloned = clone_record(db, source_record=source, user=viewer, visibility="public")
    assert cloned.id != source.id
    assert cloned.user_id == viewer.id
    assert cloned.visibility == "public"
    assert cloned.content_id != source.content_id
    assert cloned.content.filename == "doc.txt"
    assert cloned.content.oss_key != source.content.oss_key
    assert set(cloned.get_tags()) == {"tag1", "tag2"}


def test_update_record_replaces_uploaded_file(monkeypatch) -> None:
    from benoss_api.services import records_commands

    db = _make_db()
    owner = User(username="owner", role="user", is_active=True, password_hash="x")
    content = Content(
        kind="file",
        file_type="image",
        text_content="",
        oss_key="records/source/old.png",
        filename="old.png",
        content_type="image/png",
        size_bytes=3,
        sha256="old-sha",
    )
    db.add_all([owner, content])
    db.flush()

    record = Record(
        user_id=owner.id,
        content_id=content.id,
        visibility="public",
        preview="old.png",
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    replacement = Content(
        kind="file",
        file_type="document",
        text_content="",
        oss_key="records/source/new.txt",
        filename="new.txt",
        content_type="text/plain",
        size_bytes=11,
        sha256="new-sha",
    )
    monkeypatch.setattr(records_commands, "file_to_content", lambda _upload: (replacement, "new.txt"))

    upload = type("UploadStub", (), {"filename": "new.txt"})()
    updated = update_record(db, record=record, body={}, upload_file=upload)

    assert updated.content.filename == "new.txt"
    assert updated.content.oss_key == "records/source/new.txt"
    assert updated.content.content_type == "text/plain"
    assert updated.preview == "new.txt"
