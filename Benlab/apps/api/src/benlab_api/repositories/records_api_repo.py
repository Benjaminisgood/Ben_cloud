from __future__ import annotations

import json
import re
from collections import Counter
from datetime import UTC, date, datetime, time, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Attachment, Log, Member, Message

_TAG_PATTERN = re.compile(r"#([A-Za-z0-9_\-\u4e00-\u9fff]+)")
_RECORD_VIS_ACTION = "record_visibility"
_VALID_VIS = {"public", "private"}


def _day_bounds(day_text: str) -> tuple[datetime | None, datetime | None]:
    value = str(day_text or "").strip()
    if not value:
        return None, None
    try:
        day = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("invalid day format") from exc
    start = datetime.combine(day, time.min)
    end = start + timedelta(days=1)
    return start, end


def _base_records_stmt():
    return select(Message).options(selectinload(Message.sender), selectinload(Message.receiver))


def _normalize_visibility(value: str | None) -> str:
    token = str(value or "").strip().lower() or "private"
    return token if token in _VALID_VIS else "private"


def _parse_visibility_details(details: str) -> tuple[int | None, str]:
    if not details:
        return None, "private"
    try:
        payload = json.loads(details)
    except (TypeError, json.JSONDecodeError):
        return None, "private"
    if not isinstance(payload, dict):
        return None, "private"
    try:
        record_id = int(payload.get("record_id"))
    except (TypeError, ValueError):
        return None, "private"
    return record_id, _normalize_visibility(str(payload.get("visibility") or "private"))


def _visibility_map_for_ids(db: Session, record_ids: list[int]) -> dict[int, str]:
    if not record_ids:
        return {}
    pending = set(record_ids)
    out: dict[int, str] = {}

    rows = db.scalars(
        select(Log)
        .where(Log.action_type == _RECORD_VIS_ACTION)
        .order_by(Log.timestamp.desc(), Log.id.desc())
    ).all()
    for row in rows:
        record_id, visibility = _parse_visibility_details(row.details)
        if record_id is None or record_id not in pending:
            continue
        out[record_id] = visibility
        pending.remove(record_id)
        if not pending:
            break
    return out


def get_record_visibility(db: Session, *, record_id: int) -> str:
    vis = _visibility_map_for_ids(db, [record_id]).get(record_id)
    return vis or "private"


def set_record_visibility(db: Session, *, record_id: int, visibility: str, user_id: int | None = None) -> str:
    normalized = _normalize_visibility(visibility)
    row = Log(
        user_id=user_id,
        action_type=_RECORD_VIS_ACTION,
        details=json.dumps({"record_id": int(record_id), "visibility": normalized}, ensure_ascii=False),
    )
    db.add(row)
    db.commit()
    return normalized


def _scan_limit(limit: int, *, minimum: int = 320, maximum: int = 9000) -> int:
    return max(minimum, min(maximum, limit * 8))


def _query_candidates(
    db: Session,
    *,
    user_id: int | None,
    tag: str,
    day_start: datetime | None,
    day_end: datetime | None,
    before_id: int | None,
    order: str,
    limit: int,
) -> list[Message]:
    stmt = _base_records_stmt()
    if user_id is not None:
        stmt = stmt.where(Message.sender_id == user_id)
    if before_id:
        stmt = stmt.where(Message.id < before_id)
    if tag:
        tag_token = tag if tag.startswith("#") else f"#{tag}"
        stmt = stmt.where(Message.content.ilike(f"%{tag_token}%"))
    if day_start and day_end:
        stmt = stmt.where(Message.timestamp >= day_start, Message.timestamp < day_end)

    if order == "asc":
        stmt = stmt.order_by(Message.id.asc())
    else:
        stmt = stmt.order_by(Message.id.desc())

    return db.scalars(stmt.limit(_scan_limit(limit))).all()


def _can_view(viewer_id: int, is_admin: bool, message: Message, visibility: str) -> bool:
    if is_admin:
        return True
    if viewer_id in {message.sender_id, message.receiver_id}:
        return True
    return visibility == "public"


def _annotate_and_filter(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool,
    rows: list[Message],
    visibility_filter: str,
) -> list[Message]:
    vis_map = _visibility_map_for_ids(db, [row.id for row in rows])
    filtered: list[Message] = []
    normalized_filter = _normalize_visibility(visibility_filter) if visibility_filter else ""

    for row in rows:
        vis = vis_map.get(row.id, "private")
        setattr(row, "_api_visibility", vis)
        if normalized_filter and vis != normalized_filter:
            continue
        if _can_view(viewer_id, is_admin, row, vis):
            filtered.append(row)
    return filtered


def list_records(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool = False,
    user_id: int | None = None,
    tag: str = "",
    day: str = "",
    visibility: str = "",
    before_id: int | None = None,
    limit: int = 40,
) -> tuple[list[Message], bool]:
    day_start, day_end = _day_bounds(day)
    rows = _query_candidates(
        db,
        user_id=user_id,
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=before_id,
        order="desc",
        limit=limit,
    )
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter=visibility,
    )
    return visible_rows[:limit], len(visible_rows) > limit


def pull_records(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool = False,
    user_id: int | None = None,
    tag: str = "",
    before_id: int | None = None,
    limit: int = 40,
) -> tuple[list[Message], bool]:
    rows = _query_candidates(
        db,
        user_id=user_id,
        tag=tag,
        day_start=None,
        day_end=None,
        before_id=before_id,
        order="desc",
        limit=limit,
    )
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter="",
    )
    return visible_rows[:limit], len(visible_rows) > limit


def list_notice_records(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool = False,
    user_id: int | None = None,
    tag: str = "",
    day_start: datetime | None = None,
    day_end: datetime | None = None,
    before_id: int | None = None,
    limit: int = 200,
) -> list[Message]:
    rows = _query_candidates(
        db,
        user_id=user_id,
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=before_id,
        order="desc",
        limit=limit,
    )
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter="",
    )
    return visible_rows[: limit + 1]


def list_notice_render_records(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool = False,
    user_id: int | None = None,
    tag: str = "",
    day_start: datetime | None = None,
    day_end: datetime | None = None,
    order: str = "desc",
    limit: int = 100,
) -> list[Message]:
    order_token = "asc" if str(order).lower() == "asc" else "desc"
    rows = _query_candidates(
        db,
        user_id=user_id,
        tag=tag,
        day_start=day_start,
        day_end=day_end,
        before_id=None,
        order=order_token,
        limit=limit,
    )
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter="",
    )
    return visible_rows[:limit]


def get_record_detail(db: Session, record_id: int) -> Message | None:
    return db.scalar(_base_records_stmt().where(Message.id == record_id))


def get_record_by_content_id(db: Session, content_id: int) -> Message | None:
    return get_record_detail(db, content_id)


def get_content(db: Session, content_id: int) -> Attachment | None:
    return db.get(Attachment, content_id)


def create_record(db: Session, *, sender_id: int, receiver_id: int, content: str) -> Message:
    record = Message(sender_id=sender_id, receiver_id=receiver_id, content=content)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_record(db: Session, *, record: Message, content: str) -> Message:
    record.content = content
    db.commit()
    db.refresh(record)
    return record


def delete_record(db: Session, *, record: Message) -> None:
    db.delete(record)
    db.commit()


def _comment_record_id(details: str) -> int | None:
    if not details:
        return None
    try:
        payload = json.loads(details)
    except (TypeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("record_id")
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def list_comments(db: Session, *, record_id: int) -> list[Log]:
    pattern = f'%"record_id": {int(record_id)}%'
    rows = db.scalars(
        select(Log)
        .options(selectinload(Log.user))
        .where(Log.action_type == "record_comment", Log.details.like(pattern))
        .order_by(Log.timestamp.asc(), Log.id.asc())
    ).all()
    return [row for row in rows if _comment_record_id(row.details) == record_id]


def create_comment(db: Session, *, record_id: int, user_id: int, body: str) -> Log:
    details = json.dumps({"record_id": int(record_id), "body": str(body or "")}, ensure_ascii=False)
    comment = Log(user_id=user_id, action_type="record_comment", details=details)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


def list_tags(
    db: Session,
    *,
    viewer_id: int,
    is_admin: bool = False,
    q: str = "",
    limit: int = 20,
) -> list[str]:
    rows = db.scalars(select(Message).order_by(Message.id.desc()).limit(9000)).all()
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter="",
    )

    counter: Counter[str] = Counter()
    for row in visible_rows:
        for tag in _TAG_PATTERN.findall(str(row.content or "")):
            counter[tag] += 1
    q_norm = str(q or "").strip().lower()
    names = [name for name, _count in counter.most_common() if not q_norm or q_norm in name.lower()]
    return names[:limit]


def get_attachment(db: Session, attachment_id: int) -> Attachment | None:
    return db.get(Attachment, attachment_id)


def count_records(db: Session, *, viewer_id: int | None = None, is_admin: bool = False) -> int:
    if viewer_id is None or is_admin:
        return int(db.scalar(select(func.count(Message.id))) or 0)

    rows = db.scalars(select(Message.id).order_by(Message.id.desc()).limit(9000)).all()
    vis_map = _visibility_map_for_ids(db, [int(rid) for rid in rows])
    visible_ids: list[int] = []
    for rid in rows:
        msg = db.get(Message, rid)
        if not msg:
            continue
        vis = vis_map.get(msg.id, "private")
        if _can_view(viewer_id, False, msg, vis):
            visible_ids.append(msg.id)
    return len(visible_ids)


def count_users(db: Session) -> int:
    return int(db.scalar(select(func.count(Member.id))) or 0)


def list_recent_records(
    db: Session,
    *,
    viewer_id: int | None = None,
    is_admin: bool = False,
    limit: int = 10,
) -> list[Message]:
    rows = db.scalars(_base_records_stmt().order_by(Message.id.desc()).limit(_scan_limit(limit))).all()
    if viewer_id is None:
        return rows[:limit]
    visible_rows = _annotate_and_filter(
        db,
        viewer_id=viewer_id,
        is_admin=is_admin,
        rows=rows,
        visibility_filter="",
    )
    return visible_rows[:limit]


def list_recent_attachments(db: Session, *, limit: int = 5) -> list[Attachment]:
    return db.scalars(select(Attachment).order_by(Attachment.created_at.desc(), Attachment.id.desc()).limit(limit)).all()


def list_top_tags(
    db: Session,
    *,
    viewer_id: int | None = None,
    is_admin: bool = False,
    limit: int = 10,
) -> list[tuple[str, int]]:
    rows = db.scalars(select(Message).order_by(Message.id.desc()).limit(9000)).all()
    if viewer_id is not None:
        rows = _annotate_and_filter(
            db,
            viewer_id=viewer_id,
            is_admin=is_admin,
            rows=rows,
            visibility_filter="",
        )

    counter: Counter[str] = Counter()
    for row in rows:
        for tag in _TAG_PATTERN.findall(str(row.content or "")):
            counter[tag] += 1
    return counter.most_common(limit)


def now_utc_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
