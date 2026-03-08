from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, EventParticipant, Item, Location, Log, Member, MemberConnection, Message


def get_dashboard_counts(db: Session) -> dict[str, int]:
    return {
        "item_count": db.scalar(select(func.count(Item.id))) or 0,
        "location_count": db.scalar(select(func.count(Location.id))) or 0,
        "member_count": db.scalar(select(func.count(Member.id))) or 0,
        "event_count": db.scalar(select(func.count(Event.id))) or 0,
    }


def list_upcoming_events(db: Session, *, now: datetime, limit: int = 8) -> list[Event]:
    return db.scalars(
        select(Event)
        .where((Event.start_time.is_(None)) | (Event.start_time >= now))
        .order_by(Event.start_time.asc().nulls_last(), Event.id.desc())
        .limit(limit)
    ).all()


def list_recent_logs(db: Session, *, limit: int = 12) -> list[Log]:
    return db.scalars(
        select(Log)
        .options(selectinload(Log.user), selectinload(Log.item), selectinload(Log.location), selectinload(Log.event))
        .order_by(Log.timestamp.desc())
        .limit(limit)
    ).all()


def list_graph_members(db: Session, *, current_member_id: int, limit: int = 12) -> list[Member]:
    return db.scalars(
        select(Member)
        .where(Member.id != current_member_id)
        .options(
            selectinload(Member.outbound_connections).selectinload(MemberConnection.target_member),
            selectinload(Member.following),
            selectinload(Member.responsible_locations),
            selectinload(Member.items),
        )
        .order_by(Member.last_modified.desc(), Member.id.desc())
        .limit(limit)
    ).all()


def list_graph_items(db: Session, *, current_member_id: int, limit: int = 12) -> list[Item]:
    return db.scalars(
        select(Item)
        .join(Item.responsible_members)
        .where(Member.id == current_member_id)
        .options(selectinload(Item.responsible_members), selectinload(Item.locations))
        .order_by(Item.last_modified.desc())
        .limit(limit)
    ).all()


def list_graph_locations(db: Session, *, current_member_id: int, limit: int = 12) -> list[Location]:
    return db.scalars(
        select(Location)
        .join(Location.responsible_members)
        .where(Member.id == current_member_id)
        .options(
            selectinload(Location.parent),
            selectinload(Location.children),
            selectinload(Location.responsible_members),
            selectinload(Location.items),
        )
        .order_by(Location.last_modified.desc())
        .limit(limit)
    ).all()


def list_graph_events(db: Session, *, current_member_id: int, limit: int = 12) -> list[Event]:
    return db.scalars(
        select(Event)
        .where(
            (Event.owner_id == current_member_id)
            | (Event.id.in_(select(EventParticipant.event_id).where(EventParticipant.member_id == current_member_id)))
        )
        .options(
            selectinload(Event.owner),
            selectinload(Event.participant_links).selectinload(EventParticipant.member),
            selectinload(Event.items).selectinload(Item.locations),
            selectinload(Event.locations).selectinload(Location.parent),
        )
        .order_by(Event.updated_at.desc())
        .limit(limit)
    ).all()


def get_graph_center_member(db: Session, *, current_member_id: int) -> Member | None:
    return db.scalar(
        select(Member)
        .where(Member.id == current_member_id)
        .options(
            selectinload(Member.outbound_connections).selectinload(MemberConnection.target_member),
            selectinload(Member.following),
            selectinload(Member.items).selectinload(Item.locations),
            selectinload(Member.responsible_locations).selectinload(Location.parent),
            selectinload(Member.responsible_locations).selectinload(Location.children),
        )
    )


def search_items(db: Session, *, keyword: str, limit: int = 30) -> list[Item]:
    query = select(Item).order_by(Item.last_modified.desc()).limit(limit)
    if keyword:
        query = query.where(Item.name.ilike(f"%{keyword}%"))
    return db.scalars(query).all()


def search_locations(db: Session, *, keyword: str, limit: int = 30) -> list[Location]:
    query = select(Location).order_by(Location.last_modified.desc()).limit(limit)
    if keyword:
        query = query.where(Location.name.ilike(f"%{keyword}%"))
    return db.scalars(query).all()


def list_export_items(db: Session) -> list[Item]:
    return db.scalars(select(Item).options(selectinload(Item.responsible_members), selectinload(Item.locations))).all()


def list_export_members(db: Session) -> list[Member]:
    return db.scalars(select(Member)).all()


def list_export_locations(db: Session) -> list[Location]:
    return db.scalars(select(Location).options(selectinload(Location.responsible_members))).all()


def list_export_logs(db: Session) -> list[Log]:
    return db.scalars(select(Log).order_by(Log.timestamp.desc())).all()


def list_export_messages(db: Session) -> list[Message]:
    return db.scalars(select(Message).order_by(Message.timestamp.desc())).all()
