from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class RunOut(ORM):
    id: UUID
    client_id: UUID
    trigger: str
    status: str
    match_count: int
    screened_names: list[Any]
    watchlist_version_ids: list[Any]
    pep_declared: bool
    started_by: UUID | None
    created_at: datetime
    completed_at: datetime | None


class MatchReviewIn(BaseModel):
    decision: Literal["true_match", "false_positive", "needs_info"]
    note: str = Field(min_length=3, max_length=2000)


class PepDeclarationIn(BaseModel):
    is_pep: bool
    details: str | None = None


class WatchlistVersionOut(ORM):
    id: UUID
    source: str
    version_label: str
    entry_count: int
    is_current: bool
    fetched_at: datetime


class ScreeningOut(BaseModel):
    runs: list[RunOut]
    matches: list[dict[str, Any]]
