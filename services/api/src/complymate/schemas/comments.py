from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class CommentIn(BaseModel):
    resource_type: str
    resource_id: str
    body: str = Field(min_length=1, max_length=5000)


class CommentUpdate(BaseModel):
    body: str = Field(min_length=1, max_length=5000)


class CommentOut(ORM):
    id: UUID
    resource_type: str
    resource_id: str
    author_id: UUID
    body: str
    created_at: datetime
    edited_at: datetime | None
    author_name: str | None = None
