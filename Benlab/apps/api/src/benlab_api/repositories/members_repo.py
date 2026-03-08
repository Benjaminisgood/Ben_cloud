from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, EventParticipant, Item, Location, Member, MemberConnection, Message


def list_members_for_listing(db: Session) -> list[Member]:
    return db.scalars(
        select(Member)
        .options(
            selectinload(Member.followers),
            selectinload(Member.following),
            selectinload(Member.outbound_connections).selectinload(MemberConnection.target_member),
        )
        .order_by(Member.name.asc(), Member.username.asc())
    ).all()


def get_member(db: Session, *, member_id: int) -> Member | None:
    return db.get(Member, member_id)


def get_member_with_following(db: Session, *, member_id: int) -> Member | None:
    return db.scalar(select(Member).where(Member.id == member_id).options(selectinload(Member.following)))


def get_member_for_profile(db: Session, *, member_id: int) -> Member | None:
    return db.scalar(
        select(Member)
        .where(Member.id == member_id)
        .options(
            selectinload(Member.followers),
            selectinload(Member.following),
            selectinload(Member.items).selectinload(Item.locations),
            selectinload(Member.responsible_locations),
            selectinload(Member.sent_messages),
            selectinload(Member.received_messages),
            selectinload(Member.outbound_connections).selectinload(MemberConnection.target_member),
        )
    )


def list_member_owned_events(db: Session, *, member_id: int, limit: int = 15) -> list[Event]:
    return db.scalars(
        select(Event)
        .where(Event.owner_id == member_id)
        .order_by(Event.updated_at.desc())
        .limit(limit)
    ).all()


def list_member_participating_events(db: Session, *, member_id: int, limit: int = 15) -> list[Event]:
    return db.scalars(
        select(Event)
        .join(EventParticipant, EventParticipant.event_id == Event.id)
        .where(EventParticipant.member_id == member_id)
        .order_by(Event.updated_at.desc())
        .limit(limit)
    ).all()


def list_member_recent_messages(db: Session, *, member_id: int, limit: int = 20) -> list[Message]:
    return db.scalars(
        select(Message)
        .where(or_(Message.sender_id == member_id, Message.receiver_id == member_id))
        .order_by(Message.timestamp.desc())
        .limit(limit)
    ).all()


def list_profile_edit_options(db: Session) -> tuple[list[Event], list[Item], list[Location]]:
    events = db.scalars(select(Event).order_by(func.lower(Event.title), Event.id.asc())).all()
    items = db.scalars(select(Item).order_by(func.lower(Item.name), Item.id.asc())).all()
    locations = db.scalars(select(Location).order_by(func.lower(Location.name), Location.id.asc())).all()
    return events, items, locations


def list_profile_relation_targets(
    db: Session,
    *,
    event_ids: list[int],
    item_ids: list[int],
    location_ids: list[int],
) -> tuple[list[Event], list[Item], list[Location]]:
    events = db.scalars(select(Event).where(Event.id.in_(event_ids))).all() if event_ids else []
    items = db.scalars(select(Item).where(Item.id.in_(item_ids))).all() if item_ids else []
    locations = db.scalars(select(Location).where(Location.id.in_(location_ids))).all() if location_ids else []
    return events, items, locations


def list_member_connection_candidates(db: Session, *, exclude_member_id: int) -> list[Member]:
    return db.scalars(
        select(Member)
        .where(Member.id != exclude_member_id)
        .order_by(func.lower(Member.name), Member.id.asc())
    ).all()


def list_member_connections(db: Session, *, source_member_id: int) -> list[MemberConnection]:
    return db.scalars(
        select(MemberConnection)
        .where(MemberConnection.source_member_id == source_member_id)
        .options(selectinload(MemberConnection.target_member))
        .order_by(MemberConnection.updated_at.desc(), MemberConnection.id.desc())
    ).all()


def username_exists_excluding(db: Session, *, username: str, member_id: int) -> bool:
    return db.scalar(select(Member).where(Member.username == username, Member.id != member_id)) is not None
