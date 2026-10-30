from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from complymate.schemas.common import ORM


class TaskOut(ORM):
    id: UUID
    type: str
    title: str
    description: str | None
    resource_type: str | None
    resource_id: str | None
    assignee_id: UUID | None
    created_by: UUID | None
    status: str
    due_date: date | None
    escalated_at: datetime | None
    completed_at: datetime | None
    created_at: datetime


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    description: str | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
    resource_type: str | None = None
    resource_id: str | None = None


class TaskUpdate(BaseModel):
    status: Literal["open", "done", "cancelled"] | None = None
    assignee_id: UUID | None = None
    due_date: date | None = None
