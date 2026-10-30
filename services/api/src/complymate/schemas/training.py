from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class ModuleOut(ORM):
    id: UUID
    title: str
    description: str | None
    roles: list[str]
    jurisdiction: str
    duration_minutes: int
    pass_mark: int
    status: str
    version: int


class QuestionPublic(BaseModel):
    id: UUID
    question: str
    options: list[str]


class ModuleDetail(ModuleOut):
    content_md: str
    questions: list[QuestionPublic]


class AttemptIn(BaseModel):
    answers: dict[str, int]


class AttemptOut(ORM):
    id: UUID
    module_id: UUID
    user_id: UUID
    score: Decimal
    passed: bool
    completed_at: datetime
    certificate_key: str | None = None


class AttemptResult(BaseModel):
    attempt: AttemptOut
    feedback: list[dict[str, Any]]


class AssignmentIn(BaseModel):
    module_id: UUID
    user_ids: list[UUID]
    due_date: date | None = None


class AssignmentOut(ORM):
    id: UUID
    module_id: UUID
    user_id: UUID
    due_date: date | None
    completed_at: datetime | None


class ModuleUpsert(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    content_md: str = ""
    roles: list[str] = []
    jurisdiction: str = "AU"
    duration_minutes: int = 15
    pass_mark: int = Field(default=80, ge=1, le=100)
    status: str = "draft"


class QuizQuestionOut(ORM):
    id: UUID
    module_id: UUID
    question: str
    options: list[str]
    correct_index: int
    explanation: str | None
    source_citation: dict[str, Any] | None
    review_status: str
    ai_generated: bool


class QuizReviewIn(BaseModel):
    review_status: str
    question: str | None = None
    options: list[str] | None = None
    correct_index: int | None = None
    explanation: str | None = None
