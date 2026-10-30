from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TenantSummary(BaseModel):
    id: UUID
    name: str
    jurisdiction: str
    status: str
    plan_code: str
    created_at: datetime
    members: int
    usage: dict[str, int]
    subscription_status: str | None


class TenantStatusIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class FlagIn(BaseModel):
    key: str
    enabled: bool
    tenant_id: UUID | None = None


class KbSourceIn(BaseModel):
    jurisdiction: str = Field(pattern="^(AU|NZ)$")
    title: str
    url: str | None = None
    publisher: str = "AUSTRAC"
    doc_type: str = "guidance"
    content: str = Field(min_length=50)


class KbSourceOut(BaseModel):
    id: UUID
    jurisdiction: str
    title: str
    url: str | None
    publisher: str
    status: str
    chunk_count: int
    last_checked_at: datetime | None
    indexed_at: datetime | None


class LastCheckedIn(BaseModel):
    last_checked_at: datetime | None = None


class GenerateQuizIn(BaseModel):
    module_id: UUID
    count: int = Field(default=5, ge=1, le=15)


class ImpersonationRequestIn(BaseModel):
    tenant_id: UUID
    reason: str
    minutes: int = 30


class ImpersonationOut(BaseModel):
    id: UUID
    tenant_id: UUID
    support_user_id: UUID
    reason: str
    duration_minutes: int
    consented_at: datetime | None
    expires_at: datetime | None
    ended_at: datetime | None
    created_at: datetime


class FeedbackResolveIn(BaseModel):
    resolution: str


class HealthOut(BaseModel):
    database: str
    jobs: dict[str, Any]
    chain_verifications: list[dict[str, Any]]
    llm_spend_month_usd: float
    llm_budget_usd: float
