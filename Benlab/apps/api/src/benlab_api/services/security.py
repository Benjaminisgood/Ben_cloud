from __future__ import annotations

def hash_password(password: str) -> str:
    from werkzeug.security import generate_password_hash

    return generate_password_hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    from werkzeug.security import check_password_hash

    if not password_hash:
        return False
    return check_password_hash(password_hash, password)
