from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from benlab_api.models import Event, Item, Location, Member


def list_items_for_overview(db: Session) -> list[Item]:
    return db.scalars(
        select(Item)
        .options(
            selectinload(Item.responsible_members),
            selectinload(Item.locations),
            selectinload(Item.attachments),
        )
        .order_by(Item.last_modified.desc(), Item.id.desc())
    ).all()


def list_item_form_options(db: Session) -> tuple[list[Member], list[Location]]:
    members = db.scalars(select(Member).order_by(Member.name.asc(), Member.username.asc())).all()
    locations = db.scalars(select(Location).order_by(Location.name.asc())).all()
    return members, locations


def list_non_empty_categories(db: Session) -> list[str]:
    categories = db.scalars(select(Item.category).where(Item.category.isnot(None))).all()
    return sorted({(category or "").strip() for category in categories if (category or "").strip()})


def get_item(db: Session, *, item_id: int) -> Item | None:
    return db.get(Item, item_id)


def get_item_for_detail(db: Session, *, item_id: int) -> Item | None:
    return db.scalar(
        select(Item)
        .where(Item.id == item_id)
        .options(
            selectinload(Item.events).selectinload(Event.participant_links),
            selectinload(Item.responsible_members),
            selectinload(Item.locations),
            selectinload(Item.attachments),
        )
    )


def list_members_by_ids(db: Session, *, member_ids: list[int]) -> list[Member]:
    if not member_ids:
        return []
    return db.scalars(select(Member).where(Member.id.in_(member_ids))).all()


def list_locations_by_ids(db: Session, *, location_ids: list[int]) -> list[Location]:
    if not location_ids:
        return []
    return db.scalars(select(Location).where(Location.id.in_(location_ids))).all()


def list_items_by_ids(db: Session, *, item_ids: list[int]) -> list[Item]:
    if not item_ids:
        return []
    return db.scalars(select(Item).where(Item.id.in_(item_ids))).all()


def list_categorized_items(db: Session) -> list[Item]:
    return db.scalars(
        select(Item)
        .where(Item.category.isnot(None), Item.category != "")
        .order_by(Item.category.asc(), Item.name.asc())
    ).all()


def list_uncategorized_items(db: Session) -> list[Item]:
    return db.scalars(
        select(Item)
        .where(or_(Item.category.is_(None), Item.category == ""))
        .order_by(Item.name.asc())
    ).all()
