from __future__ import annotations

from sqlalchemy.orm import Session

from benlab_api.models import Log


def record_log(
    db: Session,
    *,
    user_id: int | None,
    action_type: str,
    details: str = "",
    item_id: int | None = None,
    location_id: int | None = None,
    event_id: int | None = None,
) -> None:
    db.add(
        Log(
            user_id=user_id,
            action_type=action_type,
            details=details,
            item_id=item_id,
            location_id=location_id,
            event_id=event_id,
        )
    )
