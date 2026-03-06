from __future__ import annotations

from sqlalchemy import Column, ForeignKey, Integer, Table

from benlab_api.db.base import Base


item_members = Table(
    "item_members",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
)

item_locations = Table(
    "item_locations",
    Base.metadata,
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
)

location_members = Table(
    "location_members",
    Base.metadata,
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("member_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
)

member_follows = Table(
    "member_follows",
    Base.metadata,
    Column("follower_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
    Column("followed_id", Integer, ForeignKey("members.id", ondelete="CASCADE"), primary_key=True),
)


# m2m links from events

event_items = Table(
    "event_items",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("item_id", Integer, ForeignKey("items.id", ondelete="CASCADE"), primary_key=True),
)

event_locations = Table(
    "event_locations",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
)
