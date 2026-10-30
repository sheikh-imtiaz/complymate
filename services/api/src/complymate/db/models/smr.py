from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin, TimestampMixin


class SmrCase(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "smr_cases"

    reference: Mapped[str] = mapped_column(String(30))
    client_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    raised_by: Mapped[uuid.UUID]
    assigned_to: Mapped[uuid.UUID | None]
    summary: Mapped[str] = mapped_column(Text)
    grounds: Mapped[str | None] = mapped_column(Text)
    suspicion_categories: Mapped[list[Any]] = mapped_column(default=list)
    transaction_details: Mapped[dict[str, Any]] = mapped_column(default=dict)
    austrac_fields: Mapped[dict[str, Any]] = mapped_column(default=dict)
    ai_suggestion: Mapped[dict[str, Any] | None]
    decision_reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[uuid.UUID | None]
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    exported_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SmrNote(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "smr_notes"

    case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("smr_cases.id", ondelete="CASCADE"), index=True)
    author_id: Mapped[uuid.UUID]
    body: Mapped[str] = mapped_column(Text)
