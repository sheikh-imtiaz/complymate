from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class SmrCreate(BaseModel):
    client_id: UUID | None = None
    summary: str = Field(min_length=10, max_length=10_000)
    transaction_details: dict[str, Any] = {}


class SmrUpdate(BaseModel):
    grounds: str | None = None
    suspicion_categories: list[str] | None = None
    transaction_details: dict[str, Any] | None = None
    austrac_fields: dict[str, Any] | None = None
    assigned_to: UUID | None = None


class SmrOut(ORM):
    id: UUID
    reference: str
    client_id: UUID | None
    status: str
    raised_by: UUID
    assigned_to: UUID | None
    summary: str
    grounds: str | None
    suspicion_categories: list[str]
    transaction_details: dict[str, Any]
    austrac_fields: dict[str, Any]
    ai_suggestion: dict[str, Any] | None
    decision_reason: str | None
    decided_by: UUID | None
    decided_at: datetime | None
    exported_at: datetime | None
    created_at: datetime
    updated_at: datetime


class SmrNoteIn(BaseModel):
    body: str = Field(min_length=1, max_length=10_000)


class SmrNoteOut(ORM):
    id: UUID
    author_id: UUID
    body: str
    created_at: datetime


class SmrDecisionIn(BaseModel):
    report: bool
    reason: str = Field(min_length=10, max_length=5000)


class SmrDetail(BaseModel):
    case: SmrOut
    notes: list[SmrNoteOut]
    tipping_off_warning: str
