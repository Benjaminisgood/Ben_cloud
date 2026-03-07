from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ClipboardItemCreate(BaseModel):
    content: str
    content_type: str = "text/plain"
    is_public: bool = False
    expires_in_hours: Optional[int] = None  # If None, use default from config


class ClipboardItemResponse(BaseModel):
    id: int
    content: str
    content_type: str
    created_at: datetime
    expires_at: Optional[datetime]
    is_public: bool
    access_token: Optional[str]

    class Config:
        from_attributes = True


class FileUploadResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    content_type: Optional[str]
    created_at: datetime
    expires_at: Optional[datetime]
    is_public: bool
    download_count: int
    access_token: Optional[str]
    upload_status: str

    class Config:
        from_attributes = True


class FileUploadInitRequest(BaseModel):
    filename: str
    file_size: int
    content_type: Optional[str] = None
    chunk_count: int = 1
    is_public: bool = False
    expires_in_hours: Optional[int] = None


class FileUploadInitResponse(BaseModel):
    upload_id: int
    access_token: str
    oss_key: str
    chunk_upload_urls: list[str] = Field(default_factory=list)  # For multipart upload
    multipart_upload_id: Optional[str] = None
    complete_upload_url: str


class FilePartETag(BaseModel):
    part_number: int = Field(ge=1)
    etag: str


class FileUploadCompleteRequest(BaseModel):
    multipart_upload_id: Optional[str] = None
    parts: list[FilePartETag] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    service: str = "benfer"
