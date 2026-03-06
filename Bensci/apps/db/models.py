from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, LargeBinary, String, Table, Text, UniqueConstraint, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


article_tags = Table(
    "article_tags",
    Base.metadata,
    Column("article_id", ForeignKey("articles.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Article(Base):
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True)
    doi: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default="")
    keywords: Mapped[str] = mapped_column(Text, default="")
    abstract: Mapped[str] = mapped_column(Text, default="")
    journal: Mapped[str] = mapped_column(String(512), default="")
    corresponding_author: Mapped[str] = mapped_column(String(512), default="")
    affiliations: Mapped[str] = mapped_column(Text, default="")
    source: Mapped[str] = mapped_column(String(128), default="")
    publisher: Mapped[str] = mapped_column(String(256), default="")
    published_date: Mapped[str] = mapped_column(String(32), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    note: Mapped[str] = mapped_column(Text, default="")
    check_status: Mapped[str] = mapped_column(String(16), default="unchecked")
    citation_count: Mapped[int | None] = mapped_column(default=None)
    impact_factor: Mapped[float | None] = mapped_column(default=None)
    embedding_vector: Mapped[bytes | None] = mapped_column(LargeBinary, default=None)
    embedding_model: Mapped[str | None] = mapped_column(String(128), default=None)
    embedding_dimensions: Mapped[int | None] = mapped_column(default=None)
    embedding_text_hash: Mapped[str | None] = mapped_column(String(64), default=None)
    embedding_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=article_tags,
        back_populates="articles",
        lazy="selectin",
    )


class Tag(Base):
    __tablename__ = "tags"
    __table_args__ = (UniqueConstraint("name", name="uq_tag_name"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), index=True)

    articles: Mapped[list[Article]] = relationship(
        secondary=article_tags,
        back_populates="tags",
        lazy="selectin",
    )


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24), index=True, default="queued")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str] = mapped_column(Text, default="{}")
    log_text: Mapped[str] = mapped_column(Text, default="")
    error: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class RuntimeSetting(Base):
    __tablename__ = "runtime_settings"

    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LLMQueryFilterKept(Base):
    __tablename__ = "llm_query_filter_kept"
    __table_args__ = (UniqueConstraint("doi", "decision_scope_hash", name="uq_llm_query_filter_kept_doi_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doi: Mapped[str] = mapped_column(String(255), index=True)
    decision_scope_hash: Mapped[str] = mapped_column(String(64), index=True)
    decision_scope_text: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(default=None)
    reason: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    prompt_tokens: Mapped[int | None] = mapped_column(default=None)
    completion_tokens: Mapped[int | None] = mapped_column(default=None)
    total_tokens: Mapped[int | None] = mapped_column(default=None)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class LLMQueryFilterDropped(Base):
    __tablename__ = "llm_query_filter_dropped"
    __table_args__ = (UniqueConstraint("doi", "decision_scope_hash", name="uq_llm_query_filter_dropped_doi_scope"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    doi: Mapped[str] = mapped_column(String(255), index=True)
    decision_scope_hash: Mapped[str] = mapped_column(String(64), index=True)
    decision_scope_text: Mapped[str] = mapped_column(Text, default="")
    score: Mapped[float | None] = mapped_column(default=None)
    reason: Mapped[str] = mapped_column(Text, default="")
    model_name: Mapped[str] = mapped_column(String(128), default="")
    prompt_tokens: Mapped[int | None] = mapped_column(default=None)
    completion_tokens: Mapped[int | None] = mapped_column(default=None)
    total_tokens: Mapped[int | None] = mapped_column(default=None)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
