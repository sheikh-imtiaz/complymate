"""Copies new audit events to the immutable sink (S3 Object Lock compliance mode / Blob immutable storage)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from complymate.container import get_container
from complymate.db.models import AuditArchiveCursor
from complymate.db.repositories.audit import AuditRepo
from complymate.db.session import tenant_session
from complymate.workers._common import active_tenant_ids

BATCH = 5000


async def _archive(tenant_id: UUID | None) -> int:
    container = get_container()
    key = str(tenant_id) if tenant_id else "platform"
    async with tenant_session(tenant_id, platform=tenant_id is None) as session:
        cursor = (
            await session.execute(select(AuditArchiveCursor).where(AuditArchiveCursor.tenant_key == key))
        ).scalar_one_or_none()
        if cursor is None:
            cursor = AuditArchiveCursor(tenant_key=key, last_seq=0)
            session.add(cursor)
        events = []
        async for e in AuditRepo(session).iter_chain(tenant_id, after_seq=cursor.last_seq):
            events.append(e)
            if len(events) >= BATCH:
                break
        if not events:
            return 0
        batch_key = f"{datetime.now(UTC):%Y/%m/%d}/{events[0]['seq']:012d}-{events[-1]['seq']:012d}"
        location = await container.audit_sink.write_batch(key, batch_key, events)
        cursor.last_seq = events[-1]["seq"]
        cursor.last_location = location
        cursor.updated_at = datetime.now(UTC)
        return len(events)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    total = 0
    for tenant_id in [None, *await active_tenant_ids()]:
        total += await _archive(tenant_id)
    return {"archived": total}
