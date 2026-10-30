from __future__ import annotations

from datetime import datetime
from uuid import UUID

from complymate.schemas.common import ORM


class NotificationOut(ORM):
    id: UUID
    kind: str
    title: str
    body: str | None
    link: str | None
    read_at: datetime | None
    created_at: datetime
