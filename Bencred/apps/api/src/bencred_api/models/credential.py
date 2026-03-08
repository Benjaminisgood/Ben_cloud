"""Credential model for secure storage."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from bencred_api.db.base import Base


class Credential(Base):
    """Secure credential storage model."""
    
    __tablename__ = "credentials"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    credential_type: Mapped[str] = mapped_column(String(100), nullable=False)  # api_key, password, oauth, etc.
    
    # Encrypted storage
    encrypted_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON encrypted with Fernet
    
    # Metadata
    service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    username: Mapped[str | None] = mapped_column(String(255), nullable=True)
    endpoint: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Organization
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # cloud, database, email, etc.
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of tags

    # Review workflow
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="agent", nullable=False)
    source_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sensitivity: Mapped[str] = mapped_column(String(20), default="high", nullable=False)
    agent_access: Mapped[str] = mapped_column(String(30), default="approval_required", nullable=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_rotated: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rotation_reminder_days: Mapped[int | None] = mapped_column(Integer, default=90)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Credential(id={self.id}, name={self.name}, type={self.credential_type})>"
