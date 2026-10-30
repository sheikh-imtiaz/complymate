from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from complymate.schemas.common import ORM


class InvitationCreate(BaseModel):
    email: EmailStr
    full_name: str | None = None
    role_key: str


class InvitationOut(ORM):
    id: UUID
    email: str
    full_name: str | None
    role_id: UUID
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationCreated(InvitationOut):
    accept_url: str | None = None


class AcceptIn(BaseModel):
    token: str
