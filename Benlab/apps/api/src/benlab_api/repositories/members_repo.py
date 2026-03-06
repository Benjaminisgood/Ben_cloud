from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, EventParticipant, Item, Location, Member, Message


def list_members_for_listing(db: Session) -> list[Member]:
    return db.scalars(
        select(Member)
        .options(selectinload(Member.followers), selectinload(Member.following))
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


def username_exists_excluding(db: Session, *, username: str, member_id: int) -> bool:
    return db.scalar(select(Member).where(Member.username == username, Member.id != member_id)) is not None
