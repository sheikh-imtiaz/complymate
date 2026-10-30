from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Identity, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base


class AuditEventRow(Base):
    """Append-only. The app role has INSERT/SELECT only (migration 0001/0004)."""

    __tablename__ = "audit_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    seq: Mapped[int] = mapped_column(BigInteger, Identity(always=True), unique=True)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(index=True)
    actor_id: Mapped[uuid.UUID | None]
    actor_role: Mapped[str] = mapped_column(String(60))
    action: Mapped[str] = mapped_column(String(60))
    resource_type: Mapped[str] = mapped_column(String(60))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    before: Mapped[dict[str, Any] | None]
    after: Mapped[dict[str, Any] | None]
    reason: Mapped[str | None] = mapped_column(Text)
    ip: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(400))
    request_id: Mapped[str | None] = mapped_column(String(64))
    ai: Mapped[dict[str, Any] | None]
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    prev_hash: Mapped[str | None] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))


class AuditArchiveCursor(Base):
    __tablename__ = "audit_archive_cursors"

    tenant_key: Mapped[str] = mapped_column(String(40), primary_key=True)  # tenant uuid or 'platform'
    last_seq: Mapped[int] = mapped_column(BigInteger, default=0)
    last_location: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ChainVerification(Base):
    __tablename__ = "audit_chain_verifications"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID | None]
    ok: Mapped[bool]
    checked: Mapped[int]
    broken_at_id: Mapped[str | None] = mapped_column(String(64))
    reason: Mapped[str | None] = mapped_column(Text)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
