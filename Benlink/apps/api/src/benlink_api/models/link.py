"""Link model for bookmark management."""
from datetime import datetime
from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from benlink_api.db.base import Base


class Link(Base):
    """Link bookmark model."""
    
    __tablename__ = "links"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    url: Mapped[str] = mapped_column(String(2048), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # Metadata (auto-fetched)
    domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    og_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    
    # Organization
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)  # reading, reference, tool, etc.
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array of tags
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Review workflow
    review_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    source: Mapped[str] = mapped_column(String(50), default="agent", nullable=False)
    source_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Reading status
    status: Mapped[str] = mapped_column(String(50), default="unread")  # unread, reading, read, archived
    priority: Mapped[str] = mapped_column(String(20), default="normal")  # low, normal, high, urgent
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    accessed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<Link(id={self.id}, url={self.url[:50]}, title={self.title})>"
