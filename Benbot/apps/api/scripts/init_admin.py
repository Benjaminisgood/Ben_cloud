#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = API_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from benbot_api.core.config import get_settings  # noqa: E402
from benbot_api.db.session import SessionLocal  # noqa: E402
from benbot_api.repositories.users import (  # noqa: E402
    create_user,
    get_user_by_username,
    update_user_role,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create or repair a Benbot admin account."
    )
    parser.add_argument(
        "--username",
        help="Admin username (default: ADMIN_USERNAME from .env).",
    )
    parser.add_argument(
        "--password",
        help="Admin password (default: ADMIN_PASSWORD from .env).",
    )
    parser.add_argument(
        "--force-password-reset",
        action="store_true",
        help="Reset password when the target user already exists.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    settings = get_settings()

    username = (args.username or settings.ADMIN_USERNAME or "").strip()
    password = (args.password or settings.ADMIN_PASSWORD or "").strip()

    if not username:
        print("ERROR: missing username. Provide --username or set ADMIN_USERNAME in .env")
        return 2

    with SessionLocal() as db:
        existing = get_user_by_username(db, username, active_only=False)
        if existing:
            changed = False

            if existing.role != "admin":
                update_user_role(db, existing, "admin")
                changed = True

            if not existing.is_active:
                existing.is_active = True
                db.commit()
                db.refresh(existing)
                changed = True

            if args.force_password_reset:
                if not password:
                    print(
                        "ERROR: --force-password-reset requires --password "
                        "or ADMIN_PASSWORD in .env"
                    )
                    return 2
                existing.set_password(password)
                db.commit()
                db.refresh(existing)
                changed = True

            if changed:
                print(f"OK: admin user repaired -> username={existing.username}")
            else:
                print(f"OK: admin user already ready -> username={existing.username}")
            return 0

        if not password:
            print(
                "ERROR: password required to create new admin. Provide --password "
                "or set ADMIN_PASSWORD in .env"
            )
            return 2

        new_admin = create_user(
            db,
            username=username,
            password=password,
            role="admin",
            is_active=True,
        )
        print(f"OK: admin user created -> username={new_admin.username}")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
