from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr

from complymate.schemas.common import ORM


class ShareIn(BaseModel):
    resource_type: str
    resource_id: str
    advisor_email: EmailStr
    advisor_name: str | None = None
    expires_at: datetime


class ShareOut(ORM):
    id: UUID
    resource_type: str
    resource_id: str
    grantee_user_id: UUID
    granted_by: UUID
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime
