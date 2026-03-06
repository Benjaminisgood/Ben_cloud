from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, Item, Location, Member


def list_locations_for_overview(db: Session) -> list[Location]:
    return db.scalars(
        select(Location)
        .options(
            selectinload(Location.parent),
            selectinload(Location.children),
            selectinload(Location.responsible_members),
            selectinload(Location.items),
            selectinload(Location.attachments),
        )
        .order_by(Location.last_modified.desc(), Location.id.desc())
    ).all()


def list_location_form_options(db: Session, *, exclude_location_id: int | None = None) -> tuple[list[Member], list[Location]]:
    members = db.scalars(select(Member).order_by(Member.name.asc(), Member.username.asc())).all()

    query = select(Location)
    if exclude_location_id is not None:
        query = query.where(Location.id != exclude_location_id)
    locations = db.scalars(query.order_by(Location.name.asc())).all()
    return members, locations


def get_location(db: Session, *, location_id: int) -> Location | None:
    return db.get(Location, location_id)


def get_location_for_detail(db: Session, *, location_id: int) -> Location | None:
    return db.scalar(
        select(Location)
        .where(Location.id == location_id)
        .options(
            selectinload(Location.items),
            selectinload(Location.responsible_members),
            selectinload(Location.events).selectinload(Event.participant_links),
            selectinload(Location.attachments),
        )
    )


def list_members_by_ids(db: Session, *, member_ids: list[int]) -> list[Member]:
    if not member_ids:
        return []
    return db.scalars(select(Member).where(Member.id.in_(member_ids))).all()


def list_items_by_ids(db: Session, *, item_ids: list[int]) -> list[Item]:
    if not item_ids:
        return []
    return db.scalars(select(Item).where(Item.id.in_(item_ids))).all()


def list_all_items(db: Session) -> list[Item]:
    return db.scalars(select(Item).order_by(Item.name.asc())).all()
