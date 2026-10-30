from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str | None
    status: str
    role_key: str
    role_name: str
    role_id: UUID
    mfa_enrolled: bool
    last_login_at: datetime | None
    membership_id: UUID
    expires_at: datetime | None = None


class DirectoryEntry(BaseModel):
    user_id: UUID
    full_name: str | None
    email: str
    role_key: str


class RoleChangeIn(BaseModel):
    role_key: str
    reason: str | None = None
