"""Credential schemas for API validation."""
from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, Field

ReviewStatus = Literal["pending", "approved", "rejected", "archived"]
AgentAccess = Literal["read", "masked", "approval_required", "deny"]
Sensitivity = Literal["low", "medium", "high", "critical"]
SourceType = Literal["agent", "manual", "import", "api"]


class CredentialBase(BaseModel):
    """Base credential schema."""
    name: str = Field(..., min_length=1, max_length=255, description="Credential name")
    credential_type: str = Field(..., min_length=1, max_length=100, description="Type: api_key, password, oauth, etc.")
    service_name: Optional[str] = Field(None, max_length=255, description="Service name")
    username: Optional[str] = Field(None, max_length=255, description="Username or identifier")
    endpoint: Optional[str] = Field(None, max_length=500, description="API endpoint or URL")
    category: Optional[str] = Field(None, max_length=100, description="Category: cloud, database, email, etc.")
    tags: Optional[list[str]] = Field(None, description="List of tags")
    rotation_reminder_days: Optional[int] = Field(90, ge=1, le=365, description="Days until rotation reminder")
    source: SourceType = Field("agent", description="Record source")
    source_detail: Optional[str] = Field(None, description="Agent/task/source context")
    review_status: ReviewStatus = Field("pending", description="Review workflow status")
    sensitivity: Sensitivity = Field("high", description="Sensitivity classification")
    agent_access: AgentAccess = Field("approval_required", description="How agents may access this record")


class CredentialCreate(CredentialBase):
    """Schema for creating a credential."""
    secret_data: str = Field(..., min_length=1, description="Secret data to encrypt (API key, password, etc.)")


class CredentialUpdate(BaseModel):
    """Schema for updating a credential."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    secret_data: Optional[str] = Field(None, min_length=1, description="New secret data to encrypt")
    service_name: Optional[str] = Field(None, max_length=255)
    username: Optional[str] = Field(None, max_length=255)
    endpoint: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[list[str]] = None
    is_active: Optional[bool] = None
    rotation_reminder_days: Optional[int] = Field(None, ge=1, le=365)
    source: Optional[SourceType] = None
    source_detail: Optional[str] = None
    review_status: Optional[ReviewStatus] = None
    sensitivity: Optional[Sensitivity] = None
    agent_access: Optional[AgentAccess] = None
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = Field(None, max_length=255)


class CredentialReview(BaseModel):
    """Schema for reviewing a credential submission."""
    review_status: ReviewStatus = Field(..., description="Result of the review")
    review_notes: Optional[str] = Field(None, description="Reviewer notes")
    reviewed_by: Optional[str] = Field(None, max_length=255, description="Reviewer name")
    sensitivity: Optional[Sensitivity] = Field(None, description="Sensitivity classification override")
    agent_access: Optional[AgentAccess] = Field(None, description="Agent access policy override")
    is_active: Optional[bool] = Field(None, description="Optional active flag override")


class CredentialResponse(CredentialBase):
    """Schema for credential response (without secret data)."""
    id: int
    is_active: bool
    review_notes: Optional[str] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    last_rotated: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    accessed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CredentialWithSecret(CredentialResponse):
    """Schema for credential response with decrypted secret (admin only)."""
    decrypted_data: str = Field(..., description="Decrypted secret data")


class CredentialListResponse(BaseModel):
    """Paginated credential list response."""
    items: list[CredentialResponse]
    total: int
    page: int
    page_size: int
