from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class AssessmentOut(ORM):
    id: UUID
    client_id: UUID
    rules_version: str
    score: int
    level: str
    reasons: list[dict[str, Any]]
    facts: dict[str, Any]
    status: str
    override_level: str | None
    override_reason: str | None
    created_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime


class OverrideIn(BaseModel):
    level: Literal["low", "medium", "high"]
    reason: str = Field(min_length=10, max_length=2000)


class EddTaskOut(ORM):
    id: UUID
    client_id: UUID
    key: str
    title: str
    status: str
    evidence: dict[str, Any]
    completed_by: UUID | None
    completed_at: datetime | None
    due_date: date | None


class EddTaskUpdate(BaseModel):
    status: Literal["open", "done", "waived"]
    evidence: dict[str, Any] = {}
    note: str | None = None
