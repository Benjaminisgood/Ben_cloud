from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String
from werkzeug.security import check_password_hash, generate_password_hash

from ..db.base import Base
from .common import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="customer", index=True)
    full_name = Column(String(80), nullable=False, default="")
    phone = Column(String(40), nullable=False, default="")
    is_active = Column(Boolean, nullable=False, default=True, index=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password, method="pbkdf2:sha256")

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)
