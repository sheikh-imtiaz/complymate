from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr

from complymate.schemas.common import ORM


class ReportJobOut(ORM):
    id: UUID
    report_type: str
    format: str
    status: str
    schedule_cron: str | None
    recipients: list[str]
    export_id: UUID | None
    error: str | None
    created_at: datetime
    completed_at: datetime | None


class ScheduleIn(BaseModel):
    report_type: str
    format: Literal["csv", "xlsx"] = "xlsx"
    cron: str
    recipients: list[EmailStr]
    params: dict[str, Any] = {}


class ExportOut(ORM):
    id: UUID
    kind: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class DownloadOut(BaseModel):
    url: str
    filename: str
