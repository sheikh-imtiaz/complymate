from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from complymate.schemas.common import ORM


class AuditEventOut(ORM):
    id: UUID
    seq: int
    actor_id: UUID | None
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str | None
    ip: str | None
    user_agent: str | None
    request_id: str | None
    ai: dict[str, Any] | None
    occurred_at: datetime
    prev_hash: str | None
    hash: str


class ChainStatus(BaseModel):
    ok: bool
    checked: int
    broken_at_id: str | None
    reason: str | None
