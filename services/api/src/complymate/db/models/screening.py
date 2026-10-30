from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin


class WatchlistVersion(IdMixin, Base):
    """Global reference data (no tenant_id). App role: SELECT; workers write via the owner-granted role."""

    __tablename__ = "watchlist_versions"

    source: Mapped[str] = mapped_column(String(20))
    version_label: Mapped[str] = mapped_column(String(100))
    checksum: Mapped[str] = mapped_column(String(64))
    entry_count: Mapped[int] = mapped_column(default=0)
    is_current: Mapped[bool] = mapped_column(default=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class WatchlistEntryRow(IdMixin, Base):
    __tablename__ = "watchlist_entries"

    version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlist_versions.id", ondelete="CASCADE"), index=True)
    source: Mapped[str] = mapped_column(String(20))
    reference: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(20))
    primary_name: Mapped[str] = mapped_column(Text)
    aliases: Mapped[list[Any]] = mapped_column(default=list)
    normalized_names: Mapped[list[str]] = mapped_column(ARRAY(Text))
    search_text: Mapped[str] = mapped_column(Text)
    dob: Mapped[str | None] = mapped_column(String(60))
    nationality: Mapped[str | None] = mapped_column(String(200))
    program: Mapped[str | None] = mapped_column(Text)


class ScreeningRun(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "screening_runs"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    trigger: Mapped[str] = mapped_column(String(20))
    watchlist_version_ids: Mapped[list[Any]] = mapped_column(default=list)
    screened_names: Mapped[list[Any]] = mapped_column(default=list)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    match_count: Mapped[int] = mapped_column(default=0)
    pep_declared: Mapped[bool] = mapped_column(default=False)
    started_by: Mapped[uuid.UUID | None]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ScreeningMatch(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "screening_matches"

    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("screening_runs.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    party_id: Mapped[uuid.UUID | None]
    entry_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("watchlist_entries.id"))
    subject_name: Mapped[str] = mapped_column(Text)
    matched_name: Mapped[str] = mapped_column(Text)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    method: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20), default="open")
    reviewed_by: Mapped[uuid.UUID | None]
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)
