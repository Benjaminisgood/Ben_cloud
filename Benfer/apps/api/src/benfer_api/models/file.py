from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from benfer_api.db.database import Base


class ClipboardItem(Base):
    __tablename__ = "clipboard_items"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text/plain")  # text/plain, application/json, etc.
    user_id = Column(String(100), nullable=True)  # Optional: link to user if authenticated
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=False)
    access_token = Column(String(100), unique=True, index=True)  # For public sharing

    def __repr__(self):
        return f"<ClipboardItem(id={self.id}, created_at={self.created_at})>"


class FileUpload(Base):
    __tablename__ = "file_uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    oss_key = Column(String(500), nullable=False)  # OSS object key
    file_size = Column(Integer, nullable=False)
    content_type = Column(String(100), nullable=True)
    user_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    expires_at = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    download_count = Column(Integer, default=0)
    access_token = Column(String(100), unique=True, index=True)  # For public sharing
    upload_status = Column(String(20), default="completed")  # uploading, completed, failed
    chunk_count = Column(Integer, default=1)  # For resumable uploads
    total_chunks = Column(Integer, default=1)

    def __repr__(self):
        return f"<FileUpload(id={self.id}, filename={self.filename})>"
