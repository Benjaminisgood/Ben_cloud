from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FinanceRecordType = Literal[
    "income",
    "expense",
    "budget",
    "savings_goal",
    "debt",
    "investment",
    "subscription",
    "bill",
    "tax",
    "decision",
]
FinanceFlowDirection = Literal["inflow", "outflow", "neutral"]
FinancePlanningStatus = Literal["planned", "pending", "active", "settled", "cancelled", "archived"]
FinanceRiskLevel = Literal["low", "medium", "high", "critical"]
FinanceReviewStatus = Literal["pending_review", "approved", "rejected"]


class FinanceRecordCreate(BaseModel):
    record_type: FinanceRecordType
    title: str = Field(min_length=1, max_length=160)
    description: str = Field(min_length=1, max_length=4000)
    category: str = Field(min_length=1, max_length=80)
    flow_direction: FinanceFlowDirection = "neutral"
    planning_status: FinancePlanningStatus = "planned"
    risk_level: FinanceRiskLevel = "medium"
    amount: float | None = None
    currency: str = Field(default="CNY", min_length=3, max_length=8)
    account_name: str | None = Field(default=None, max_length=120)
    counterparty: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    due_on: date | None = None
    next_review_on: date | None = None
    recurrence_rule: str | None = Field(default=None, max_length=120)
    follow_up_action: str | None = Field(default=None, max_length=4000)
    agent_note: str | None = Field(default=None, max_length=4000)


class FinanceRecordUpdate(BaseModel):
    record_type: FinanceRecordType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    flow_direction: FinanceFlowDirection | None = None
    planning_status: FinancePlanningStatus | None = None
    risk_level: FinanceRiskLevel | None = None
    amount: float | None = None
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    account_name: str | None = Field(default=None, max_length=120)
    counterparty: str | None = Field(default=None, max_length=120)
    occurred_on: date | None = None
    due_on: date | None = None
    next_review_on: date | None = None
    recurrence_rule: str | None = Field(default=None, max_length=120)
    follow_up_action: str | None = Field(default=None, max_length=4000)
    agent_note: str | None = Field(default=None, max_length=4000)


class FinanceRecordReview(BaseModel):
    review_status: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=4000)


class FinanceRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    record_type: FinanceRecordType
    title: str
    description: str
    category: str
    flow_direction: FinanceFlowDirection
    planning_status: FinancePlanningStatus
    risk_level: FinanceRiskLevel
    review_status: FinanceReviewStatus
    amount: float | None
    currency: str
    account_name: str | None
    counterparty: str | None
    occurred_on: date | None
    due_on: date | None
    next_review_on: date | None
    recurrence_rule: str | None
    follow_up_action: str | None
    agent_note: str | None
    review_note: str | None
    created_by: str
    updated_by: str
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime
