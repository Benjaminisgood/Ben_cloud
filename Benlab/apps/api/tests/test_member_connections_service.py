from __future__ import annotations

from benlab_api.models import Member, MemberConnection
from benlab_api.services.member_connections import (
    apply_member_connections,
    build_member_connection_view,
    parse_member_connections_form,
)


class _DummyForm:
    def __init__(self, data: dict[str, object]):
        self._data = data

    def getlist(self, key: str):
        value = self._data.get(key, [])
        if isinstance(value, list):
            return value
        return [value]


def test_parse_member_connections_form_skips_self_and_duplicates() -> None:
    form = _DummyForm(
        {
            "connection_target_id": ["2", "1", "2", "3"],
            "connection_relation_type": ["friend", "family", "colleague", "other"],
            "connection_closeness": ["4", "5", "2", ""],
            "connection_note": ["室友", "self", "dup", "认识"],
        }
    )
    rows = parse_member_connections_form(form, source_member_id=1)
    assert rows == [
        {"target_member_id": 2, "relation_type": "friend", "closeness": 4, "note": "室友"},
        {"target_member_id": 3, "relation_type": "other", "closeness": None, "note": "认识"},
    ]


def test_apply_member_connections_updates_and_deletes() -> None:
    existing = [
        MemberConnection(source_member_id=1, target_member_id=2, relation_type="friend", closeness=3, note="old"),
        MemberConnection(source_member_id=1, target_member_id=4, relation_type="other", closeness=None, note="remove"),
    ]
    submitted = [
        {"target_member_id": 2, "relation_type": "classmate", "closeness": 5, "note": "new"},
        {"target_member_id": 3, "relation_type": "colleague", "closeness": 2, "note": "work"},
        {"target_member_id": 99, "relation_type": "friend", "closeness": 1, "note": "invalid"},
    ]
    to_upsert, to_delete = apply_member_connections(existing, submitted, valid_target_ids={2, 3})
    assert [connection.target_member_id for connection in to_delete] == [4]
    assert len(to_upsert) == 2
    assert to_upsert[0].relation_type == "classmate"
    assert to_upsert[0].closeness == 5
    assert to_upsert[1].target_member_id == 3


def test_build_member_connection_view() -> None:
    target = Member(id=2, name="Bob", username="bob", password_hash="x")
    connection = MemberConnection(source_member_id=1, target_member_id=2, relation_type="friend", closeness=4, note="很熟")
    connection.target_member = target
    rows = build_member_connection_view([connection])
    assert rows[0]["relation_label"] == "朋友"
    assert rows[0]["closeness_label"] == "亲近"
    assert rows[0]["target_member"].username == "bob"
    assert rows[0]["note"] == "很熟"
