from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, Text, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from benlab_api.db.base import Base

if TYPE_CHECKING:
    from benlab_api.models.attachment import Attachment


def _utcnow_naive() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class Publication(Base):
    """文献/论文模型，存储 DOI 和文章元数据"""
    __tablename__ = "publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    doi: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    authors: Mapped[str] = mapped_column(Text, default="")  # JSON 数组或逗号分隔的作者列表
    journal: Mapped[str] = mapped_column(String(255), default="")  # 期刊/会议名称
    publication_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    abstract: Mapped[str] = mapped_column(Text, default="")  # 摘要
    pdf_path: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 本地 PDF 文件路径
    pdf_downloaded: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    download_status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, success, failed
    download_error: Mapped[str | None] = mapped_column(Text, nullable=True)  # 下载错误信息
    metadata_source: Mapped[str] = mapped_column(String(100), default="manual")  # manual, crossref, api 等
    notes: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow_naive, onupdate=_utcnow_naive, nullable=False)

    # 关联附件（如果有额外的附件）
    attachments: Mapped[list["Attachment"]] = relationship(
        back_populates="publication",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Publication(id={self.id}, doi={self.doi}, title={self.title[:50]}...)"
