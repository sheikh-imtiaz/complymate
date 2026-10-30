from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin


class TrainingModule(IdMixin, CreatedMixin, Base):
    __tablename__ = "training_modules"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(index=True)  # NULL = platform content
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    content_md: Mapped[str] = mapped_column(Text, default="")
    roles: Mapped[list[Any]] = mapped_column(default=list)
    jurisdiction: Mapped[str] = mapped_column(String(2), default="AU")
    duration_minutes: Mapped[int] = mapped_column(default=15)
    pass_mark: Mapped[int] = mapped_column(default=80)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    version: Mapped[int] = mapped_column(default=1)


class QuizQuestion(IdMixin, CreatedMixin, Base):
    __tablename__ = "quiz_questions"

    tenant_id: Mapped[uuid.UUID | None]
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_modules.id", ondelete="CASCADE"), index=True)
    question: Mapped[str] = mapped_column(Text)
    options: Mapped[list[Any]] = mapped_column(default=list)
    correct_index: Mapped[int]
    explanation: Mapped[str | None] = mapped_column(Text)
    source_citation: Mapped[dict[str, Any] | None]
    review_status: Mapped[str] = mapped_column(String(20), default="draft")
    ai_generated: Mapped[bool] = mapped_column(default=False)
    reviewed_by: Mapped[uuid.UUID | None]


class TrainingAssignment(IdMixin, CreatedMixin, Base):
    __tablename__ = "training_assignments"

    tenant_id: Mapped[uuid.UUID] = mapped_column(index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_modules.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID]
    due_date: Mapped[date | None] = mapped_column(Date)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class QuizAttempt(IdMixin, Base):
    __tablename__ = "quiz_attempts"

    tenant_id: Mapped[uuid.UUID] = mapped_column(index=True)
    module_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("training_modules.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID]
    answers: Mapped[dict[str, Any]] = mapped_column(default=dict)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    passed: Mapped[bool]
    certificate_key: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
