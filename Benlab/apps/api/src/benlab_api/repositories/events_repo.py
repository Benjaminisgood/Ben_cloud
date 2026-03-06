from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, EventParticipant, Item, Location, Member


def list_visible_events(db: Session, *, member_id: int) -> list[Event]:
    return db.scalars(
        select(Event)
        .options(
            selectinload(Event.owner),
            selectinload(Event.participant_links),
            selectinload(Event.participants),
            selectinload(Event.items),
            selectinload(Event.locations),
        )
        .where(
            or_(
                Event.visibility == "public",
                Event.owner_id == member_id,
                Event.id.in_(
                    select(EventParticipant.event_id).where(EventParticipant.member_id == member_id)
                ),
            )
        )
        .order_by(Event.start_time.asc().nulls_last(), Event.updated_at.desc())
    ).all()


def list_form_options(db: Session) -> tuple[list[Member], list[Item], list[Location]]:
    members = db.scalars(select(Member).order_by(Member.name.asc(), Member.username.asc())).all()
    items = db.scalars(select(Item).order_by(Item.name.asc())).all()
    locations = db.scalars(select(Location).order_by(Location.name.asc())).all()
    return members, items, locations


def get_event_for_detail(db: Session, *, event_id: int) -> Event | None:
    return db.scalar(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.owner),
            selectinload(Event.participant_links).selectinload(EventParticipant.member),
            selectinload(Event.items),
            selectinload(Event.locations),
            selectinload(Event.attachments),
        )
    )


def get_event_for_edit(db: Session, *, event_id: int) -> Event | None:
    return db.scalar(
        select(Event)
        .where(Event.id == event_id)
        .options(
            selectinload(Event.participant_links),
            selectinload(Event.items),
            selectinload(Event.locations),
            selectinload(Event.attachments),
        )
    )


def get_event_with_participant_links(db: Session, *, event_id: int) -> Event | None:
    return db.scalar(select(Event).where(Event.id == event_id).options(selectinload(Event.participant_links)))


def get_event(db: Session, *, event_id: int) -> Event | None:
    return db.get(Event, event_id)


def list_valid_member_ids(db: Session, *, member_ids: list[int]) -> set[int]:
    if not member_ids:
        return set()
    return set(db.scalars(select(Member.id).where(Member.id.in_(member_ids))).all())


def list_items_by_ids(db: Session, *, item_ids: list[int]) -> list[Item]:
    if not item_ids:
        return []
    return db.scalars(select(Item).where(Item.id.in_(item_ids))).all()


def list_locations_by_ids(db: Session, *, location_ids: list[int]) -> list[Location]:
    if not location_ids:
        return []
    return db.scalars(select(Location).where(Location.id.in_(location_ids))).all()

