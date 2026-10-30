from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class DevLoginIn(BaseModel):
    email: EmailStr


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"  # noqa: S105


class MembershipOut(BaseModel):
    tenant_id: UUID
    tenant_name: str
    tenant_status: str
    role_key: str
    role_name: str
    expires_at: datetime | None = None


class MeOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str | None
    platform_role: str | None
    memberships: list[MembershipOut]
    tenant_id: UUID | None
    role_key: str | None
    permissions: list[str]
    mfa_verified: bool
    auth_time: datetime | None
    step_up_valid_until: datetime | None
    impersonation_id: UUID | None = None
    feature_flags: dict[str, bool] = {}
