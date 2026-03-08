from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PreferenceSubjectType = Literal[
    "food",
    "drink",
    "activity",
    "habit",
    "merchant",
    "brand",
    "item",
    "content",
    "place",
    "person",
    "service",
    "environment",
    "other",
]
PreferenceStance = Literal["love", "like", "dislike", "avoid", "neutral", "curious", "want_to_try"]
PreferenceTimeframe = Literal["past", "current", "future"]
PreferenceValidationState = Literal["hypothesis", "confirmed", "conflicted", "retired"]
PreferenceSourceKind = Literal["memory", "observation", "journal", "agent_inference", "manual"]
PreferenceReviewStatus = Literal["pending_review", "approved", "rejected"]


class PreferenceRecordCreate(BaseModel):
    subject_type: PreferenceSubjectType
    subject_name: str = Field(min_length=1, max_length=160)
    aspect: str = Field(min_length=1, max_length=80)
    stance: PreferenceStance
    timeframe: PreferenceTimeframe
    validation_state: PreferenceValidationState = "hypothesis"
    intensity: int = Field(default=5, ge=1, le=10)
    certainty: int = Field(default=5, ge=1, le=10)
    context: str | None = Field(default=None, max_length=120)
    merchant_name: str | None = Field(default=None, max_length=160)
    source_kind: PreferenceSourceKind = "manual"
    trigger_detail: str | None = Field(default=None, max_length=4000)
    supporting_detail: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_until: date | None = None


class PreferenceRecordUpdate(BaseModel):
    subject_type: PreferenceSubjectType | None = None
    subject_name: str | None = Field(default=None, min_length=1, max_length=160)
    aspect: str | None = Field(default=None, min_length=1, max_length=80)
    stance: PreferenceStance | None = None
    timeframe: PreferenceTimeframe | None = None
    validation_state: PreferenceValidationState | None = None
    intensity: int | None = Field(default=None, ge=1, le=10)
    certainty: int | None = Field(default=None, ge=1, le=10)
    context: str | None = Field(default=None, max_length=120)
    merchant_name: str | None = Field(default=None, max_length=160)
    source_kind: PreferenceSourceKind | None = None
    trigger_detail: str | None = Field(default=None, max_length=4000)
    supporting_detail: str | None = Field(default=None, max_length=4000)
    valid_from: date | None = None
    valid_until: date | None = None


class PreferenceRecordReview(BaseModel):
    review_status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=4000)


class PreferenceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject_type: PreferenceSubjectType
    subject_name: str
    aspect: str
    stance: PreferenceStance
    timeframe: PreferenceTimeframe
    validation_state: PreferenceValidationState
    review_status: PreferenceReviewStatus
    intensity: int
    certainty: int
    context: str | None
    merchant_name: str | None
    source_kind: PreferenceSourceKind
    trigger_detail: str | None
    supporting_detail: str | None
    review_note: str | None
    valid_from: date | None
    valid_until: date | None
    created_by: str
    updated_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
