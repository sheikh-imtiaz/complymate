from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin, TimestampMixin


class Program(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "programs"

    name: Mapped[str] = mapped_column(String(200), default="AML/CTF Program")
    status: Mapped[str] = mapped_column(String(30), default="draft")
    current_version_id: Mapped[uuid.UUID | None]
    approved_version_id: Mapped[uuid.UUID | None]
    interview_answers: Mapped[dict[str, Any]] = mapped_column(default=dict)
    risk_methodology: Mapped[dict[str, Any]] = mapped_column(default=dict)
    next_review_due: Mapped[date | None] = mapped_column(Date)
    created_by: Mapped[uuid.UUID | None]


class ProgramVersion(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "program_versions"
    __table_args__ = (UniqueConstraint("program_id", "version_number"),)

    program_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("programs.id", ondelete="CASCADE"))
    version_number: Mapped[int]
    status: Mapped[str] = mapped_column(String(30), default="draft")
    change_summary: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None]
    submitted_by: Mapped[uuid.UUID | None]
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    locked: Mapped[bool] = mapped_column(default=False)
    snapshot: Mapped[dict[str, Any] | None]
    draft_status: Mapped[str | None] = mapped_column(String(30))  # agent drafting: queued/running/done/failed


class ProgramSection(IdMixin, TenantMixin, Base):
    __tablename__ = "program_sections"
    __table_args__ = (UniqueConstraint("version_id", "key"),)

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("program_versions.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[int]
    content_html: Mapped[str] = mapped_column(Text, default="")
    citations: Mapped[list[Any]] = mapped_column(default=list)
    ai_generated: Mapped[bool] = mapped_column(default=False)
    ai_accepted: Mapped[bool | None]
    ai_draft_html: Mapped[str | None] = mapped_column(Text)
    tracked_changes: Mapped[list[Any]] = mapped_column(default=list)
    locked_by: Mapped[uuid.UUID | None]
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_by: Mapped[uuid.UUID | None]
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProgramApproval(IdMixin, TenantMixin, Base):
    __tablename__ = "program_approvals"

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("program_versions.id", ondelete="CASCADE"))
    step: Mapped[str] = mapped_column(String(30))
    decision: Mapped[str] = mapped_column(String(20))
    decided_by: Mapped[uuid.UUID]
    decided_role: Mapped[str] = mapped_column(String(60))
    comment: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
