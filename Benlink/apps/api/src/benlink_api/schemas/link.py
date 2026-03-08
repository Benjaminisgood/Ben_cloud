"""Link schemas for API validation."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

ReviewStatus = Literal["pending", "approved", "rejected", "archived"]
SourceType = Literal["agent", "manual", "import", "api"]


class LinkBase(BaseModel):
    """Base link schema."""
    url: str = Field(..., min_length=1, max_length=2048, description="Link URL")
    title: Optional[str] = Field(None, max_length=500, description="Link title")
    description: Optional[str] = Field(None, description="Link description")
    category: Optional[str] = Field(None, max_length=100, description="Category: reading, reference, tool, etc.")
    tags: Optional[list[str]] = Field(None, description="List of tags")
    notes: Optional[str] = Field(None, description="Personal notes")
    status: Optional[str] = Field("unread", description="Status: unread, reading, read, archived")
    priority: Optional[str] = Field("normal", description="Priority: low, normal, high, urgent")
    source: SourceType = Field("agent", description="Record source")
    source_detail: Optional[str] = Field(None, description="Agent/task/source context")
    review_status: ReviewStatus = Field("pending", description="Review workflow status")


class LinkCreate(LinkBase):
    """Schema for creating a link."""
    pass


class LinkUpdate(BaseModel):
    """Schema for updating a link."""
    title: Optional[str] = Field(None, max_length=500)
    description: Optional[str] = Field(None)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    notes: Optional[str] = Field(None)
    status: Optional[str] = Field(None)
    priority: Optional[str] = Field(None)
    is_active: Optional[bool] = None
    is_favorite: Optional[bool] = None
    source: Optional[SourceType] = None
    source_detail: Optional[str] = None
    review_status: Optional[ReviewStatus] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = Field(None, max_length=255)


class LinkReview(BaseModel):
    """Schema for reviewing a link submission."""
    review_status: ReviewStatus = Field(..., description="Result of the review")
    review_notes: Optional[str] = Field(None, description="Reviewer notes")
    reviewed_by: Optional[str] = Field(None, max_length=255, description="Reviewer name")
    category: Optional[str] = Field(None, max_length=100, description="Approved category override")
    priority: Optional[str] = Field(None, description="Priority override")
    status: Optional[str] = Field(None, description="Reading status override")
    is_favorite: Optional[bool] = Field(None, description="Favorite toggle")
    is_active: Optional[bool] = Field(None, description="Optional active flag override")


class LinkResponse(LinkBase):
    """Schema for link response."""
    id: int
    domain: Optional[str] = None
    favicon_url: Optional[str] = None
    og_image: Optional[str] = None
    is_active: bool
    is_favorite: bool
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime] = None
    last_checked_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LinkListResponse(BaseModel):
    """Paginated link list response."""
    items: list[LinkResponse]
    total: int
    page: int
    page_size: int
