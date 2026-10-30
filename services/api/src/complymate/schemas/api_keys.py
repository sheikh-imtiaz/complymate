from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    permissions: list[str]
    expires_at: datetime | None = None


class ApiKeyOut(ORM):
    id: UUID
    name: str
    prefix: str
    permissions: list[str]
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class ApiKeyCreated(ApiKeyOut):
    key: str
