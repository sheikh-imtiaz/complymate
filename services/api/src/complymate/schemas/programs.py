from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class QuestionOut(BaseModel):
    id: str
    text: str
    kind: str
    sections: list[str]
    options: list[str]
    help: str


class InterviewOut(BaseModel):
    questions: list[QuestionOut]
    answers: dict[str, Any]
    progress: float


class InterviewSave(BaseModel):
    answers: dict[str, Any]


class RiskMethodologyIn(BaseModel):
    weights: dict[str, float] = Field(
        default_factory=lambda: {"customer": 1.0, "service": 1.0, "channel": 1.0, "geography": 1.0}
    )
    thresholds: dict[str, int] = Field(default_factory=lambda: {"medium": 10, "high": 20})
    notes: str | None = None


class SectionOut(ORM):
    id: UUID
    key: str
    title: str
    position: int
    content_html: str
    citations: list[dict[str, Any]]
    ai_generated: bool
    ai_accepted: bool | None
    ai_draft_html: str | None
    tracked_changes: list[dict[str, Any]]
    locked_by: UUID | None
    locked_until: datetime | None
    updated_by: UUID | None
    updated_at: datetime | None


class ApprovalOut(ORM):
    id: UUID
    step: str
    decision: str
    decided_by: UUID
    decided_role: str
    comment: str | None
    decided_at: datetime


class VersionSummary(ORM):
    id: UUID
    version_number: int
    status: str
    change_summary: str | None
    created_by: UUID | None
    submitted_by: UUID | None
    submitted_at: datetime | None
    approved_by: UUID | None
    approved_at: datetime | None
    locked: bool
    draft_status: str | None
    created_at: datetime


class VersionDetail(VersionSummary):
    sections: list[SectionOut]
    approvals: list[ApprovalOut]


class ProgramOut(BaseModel):
    id: UUID
    status: str
    current_version_id: UUID | None
    approved_version_id: UUID | None
    next_review_due: date | None
    interview_progress: float
    versions: list[VersionSummary]
    risk_methodology: dict[str, Any]


class SectionUpdate(BaseModel):
    content_html: str = Field(max_length=200_000)
    expected_updated_at: datetime | None = None


class AiDecisionIn(BaseModel):
    accept: bool


class DraftRequest(BaseModel):
    sections: list[str] | None = None


class DecisionIn(BaseModel):
    approve: bool
    comment: str | None = Field(default=None, max_length=2000)


class NewVersionIn(BaseModel):
    change_summary: str = Field(min_length=3, max_length=2000)


class CompareSection(BaseModel):
    key: str
    title: str
    changed: bool
    diff: list[str]


class PresenceOut(BaseModel):
    user_id: UUID
    full_name: str | None
    last_seen_at: datetime


ExportFormat = Literal["docx", "pdf"]
