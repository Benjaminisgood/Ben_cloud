from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

HealthDomain = Literal["habit", "diet", "mental", "exercise", "medical"]
HealthCareStatus = Literal["planned", "active", "stable", "resolved", "needs_attention", "archived"]
HealthConcernLevel = Literal["low", "medium", "high", "critical"]
HealthFrequency = Literal["once", "daily", "weekly", "monthly", "as_needed"]
HealthReviewStatus = Literal["pending_review", "approved", "rejected"]


class HealthRecordCreate(BaseModel):
    domain: HealthDomain
    title: str = Field(min_length=1, max_length=160)
    summary: str = Field(min_length=1, max_length=4000)
    care_status: HealthCareStatus = "active"
    concern_level: HealthConcernLevel = "medium"
    started_on: date | None = None
    ended_on: date | None = None
    next_review_on: date | None = None
    frequency: HealthFrequency = "once"
    metric_name: str | None = Field(default=None, max_length=80)
    metric_value: float | None = None
    metric_unit: str | None = Field(default=None, max_length=24)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    energy_score: int | None = Field(default=None, ge=1, le=10)
    pain_score: int | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    food_name: str | None = Field(default=None, max_length=160)
    exercise_name: str | None = Field(default=None, max_length=160)
    provider_name: str | None = Field(default=None, max_length=160)
    medication_name: str | None = Field(default=None, max_length=160)
    follow_up_plan: str | None = Field(default=None, max_length=4000)
    agent_note: str | None = Field(default=None, max_length=4000)


class HealthRecordUpdate(BaseModel):
    domain: HealthDomain | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    summary: str | None = Field(default=None, min_length=1, max_length=4000)
    care_status: HealthCareStatus | None = None
    concern_level: HealthConcernLevel | None = None
    started_on: date | None = None
    ended_on: date | None = None
    next_review_on: date | None = None
    frequency: HealthFrequency | None = None
    metric_name: str | None = Field(default=None, max_length=80)
    metric_value: float | None = None
    metric_unit: str | None = Field(default=None, max_length=24)
    mood_score: int | None = Field(default=None, ge=1, le=10)
    energy_score: int | None = Field(default=None, ge=1, le=10)
    pain_score: int | None = Field(default=None, ge=0, le=10)
    sleep_hours: float | None = Field(default=None, ge=0, le=24)
    food_name: str | None = Field(default=None, max_length=160)
    exercise_name: str | None = Field(default=None, max_length=160)
    provider_name: str | None = Field(default=None, max_length=160)
    medication_name: str | None = Field(default=None, max_length=160)
    follow_up_plan: str | None = Field(default=None, max_length=4000)
    agent_note: str | None = Field(default=None, max_length=4000)


class HealthRecordReview(BaseModel):
    review_status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=4000)


class HealthRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    domain: HealthDomain
    title: str
    summary: str
    care_status: HealthCareStatus
    concern_level: HealthConcernLevel
    review_status: HealthReviewStatus
    started_on: date | None
    ended_on: date | None
    next_review_on: date | None
    frequency: HealthFrequency
    metric_name: str | None
    metric_value: float | None
    metric_unit: str | None
    mood_score: int | None
    energy_score: int | None
    pain_score: int | None
    sleep_hours: float | None
    food_name: str | None
    exercise_name: str | None
    provider_name: str | None
    medication_name: str | None
    follow_up_plan: str | None
    agent_note: str | None
    review_note: str | None
    created_by: str
    updated_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
