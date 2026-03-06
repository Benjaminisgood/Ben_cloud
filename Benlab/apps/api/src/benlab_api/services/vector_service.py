from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, Item, Location, Member, Message
from benlab_api.services.admin_identity import is_admin_member
from benlab_api.services.records_service import preview_text
from benlab_api.utils.runtime_settings import get_setting_int


class VectorServiceError(Exception):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def _optional_int(value: object, *, field_name: str) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise VectorServiceError(f"{field_name} must be an integer", status_code=400) from exc


def _score_text(query: str, text: str) -> int:
    q = query.lower()
    t = text.lower()
    if not q or not t:
        return 0
    return t.count(q)


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() + "Z" if dt else None


def build_chat_response(db: Session, viewer: Member, body: Mapping[str, Any]) -> dict:
    query = str(body.get("query") or "").strip()
    if not query:
        raise VectorServiceError("query is required", status_code=400)

    top_k = _optional_int(body.get("top_k"), field_name="top_k")
    if top_k is None:
        top_k = get_setting_int("VECTOR_TOP_K", default=8)
    top_k = max(1, min(top_k, 50))
    pattern = f"%{query}%"

    candidates: list[dict[str, Any]] = []

    msg_stmt = select(Message).options(selectinload(Message.sender)).where(Message.content.ilike(pattern))
    if not is_admin_member(viewer):
        msg_stmt = msg_stmt.where(or_(Message.sender_id == viewer.id, Message.receiver_id == viewer.id))
    msg_stmt = msg_stmt.order_by(Message.id.desc()).limit(top_k * 10)
    messages = db.scalars(msg_stmt).all()
    for msg in messages:
        snippet = preview_text(msg.content or "", limit=220)
        score = _score_text(query, msg.content or "") + 5
        candidates.append(
            {
                "source_type": "message",
                "id": msg.id,
                "title": f"Message #{msg.id}",
                "snippet": snippet,
                "url": f"/api/records/{msg.id}",
                "score": score,
                "created_at": _iso(msg.timestamp),
            }
        )

    items = db.scalars(
        select(Item)
        .where(or_(Item.name.ilike(pattern), Item.notes.ilike(pattern), Item.features.ilike(pattern)))
        .order_by(Item.last_modified.desc())
        .limit(top_k * 5)
    ).all()
    for item in items:
        hay = " ".join([item.name or "", item.notes or "", item.features or ""])
        candidates.append(
            {
                "source_type": "item",
                "id": item.id,
                "title": item.name,
                "snippet": preview_text(hay, limit=220),
                "url": f"/items/{item.id}",
                "score": _score_text(query, hay) + 3,
                "created_at": _iso(item.last_modified),
            }
        )

    locations = db.scalars(
        select(Location)
        .where(or_(Location.name.ilike(pattern), Location.notes.ilike(pattern)))
        .order_by(Location.last_modified.desc())
        .limit(top_k * 5)
    ).all()
    for location in locations:
        hay = " ".join([location.name or "", location.notes or ""])
        candidates.append(
            {
                "source_type": "location",
                "id": location.id,
                "title": location.name,
                "snippet": preview_text(hay, limit=220),
                "url": f"/locations/{location.id}",
                "score": _score_text(query, hay) + 2,
                "created_at": _iso(location.last_modified),
            }
        )

    events = db.scalars(
        select(Event)
        .where(or_(Event.title.ilike(pattern), Event.description.ilike(pattern)))
        .order_by(Event.updated_at.desc())
        .limit(top_k * 5)
    ).all()
    for event in events:
        hay = " ".join([event.title or "", event.description or ""])
        candidates.append(
            {
                "source_type": "event",
                "id": event.id,
                "title": event.title,
                "snippet": preview_text(hay, limit=220),
                "url": f"/events/{event.id}",
                "score": _score_text(query, hay) + 2,
                "created_at": _iso(event.updated_at),
            }
        )

    candidates.sort(key=lambda row: (int(row.get("score") or 0), str(row.get("created_at") or "")), reverse=True)
    results = [{k: v for k, v in row.items() if k != "score"} for row in candidates[:top_k]]
    return {"results": results, "query": query, "backend": "keyword"}


def build_rebuild_response(db: Session, body: Mapping[str, Any]) -> dict:
    force = bool(body.get("force"))
    max_docs = _optional_int(body.get("max_docs"), field_name="max_docs")
    if max_docs is None:
        max_docs = get_setting_int("VECTOR_MAX_DOCS", default=4000)

    stats = {
        "messages": int(db.scalar(select(func.count(Message.id))) or 0),
        "items": int(db.scalar(select(func.count(Item.id))) or 0),
        "locations": int(db.scalar(select(func.count(Location.id))) or 0),
        "events": int(db.scalar(select(func.count(Event.id))) or 0),
    }
    return {
        "ok": True,
        "backend": "keyword",
        "force": force,
        "max_docs": max_docs,
        "stats": stats,
        "message": "Keyword index metadata refreshed.",
    }


def build_meta_response(db: Session) -> dict:
    stats = {
        "messages": int(db.scalar(select(func.count(Message.id))) or 0),
        "items": int(db.scalar(select(func.count(Item.id))) or 0),
        "locations": int(db.scalar(select(func.count(Location.id))) or 0),
        "events": int(db.scalar(select(func.count(Event.id))) or 0),
    }
    return {
        "backend": "keyword",
        "index_ready": True,
        "supports_rebuild": True,
        "doc_count": sum(stats.values()),
        "stats": stats,
    }
