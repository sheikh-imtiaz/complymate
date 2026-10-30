from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None
    client_id: UUID | None = None
    stream: bool = True


class Citation(BaseModel):
    ref: str
    title: str
    url: str | None
    publisher: str
    heading: str | None
    last_checked_at: datetime | None
    score: float


class ChatAnswer(BaseModel):
    session_id: UUID
    message_id: UUID
    answer: str
    citations: list[Citation]
    model: str
    disclaimer: str


class SessionOut(ORM):
    id: UUID
    title: str
    created_at: datetime


class MessageOut(ORM):
    id: UUID
    role: str
    content: str
    citations: list[dict[str, Any]]
    model: str | None
    created_at: datetime
    cost_usd: Decimal


class FeedbackIn(BaseModel):
    rating: Literal["helpful", "wrong"]
    comment: str | None = Field(default=None, max_length=2000)
