from __future__ import annotations

from collections.abc import AsyncIterator, Sequence
from dataclasses import asdict
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import AuditEventRow
from complymate.domain.audit.events import AuditEvent


class AuditRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def lock_tenant_chain(self, tenant_id: UUID | None) -> None:
        key = str(tenant_id) if tenant_id else "platform"
        await self.s.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:k, 0))"), {"k": f"audit:{key}"})

    async def last_hash(self, tenant_id: UUID | None) -> str | None:
        cond = AuditEventRow.tenant_id == tenant_id if tenant_id else AuditEventRow.tenant_id.is_(None)
        row = await self.s.execute(select(AuditEventRow.hash).where(cond).order_by(AuditEventRow.seq.desc()).limit(1))
        return row.scalar_one_or_none()

    async def insert(self, event: AuditEvent) -> None:
        data = asdict(event)
        data.pop("extra", None)
        self.s.add(AuditEventRow(**data))
        await self.s.flush()

    async def search(
        self,
        tenant_id: UUID | None,
        *,
        actor_id: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        action: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[Sequence[AuditEventRow], int]:
        q = select(AuditEventRow)
        q = q.where(AuditEventRow.tenant_id == tenant_id) if tenant_id else q.where(AuditEventRow.tenant_id.is_(None))
        if actor_id:
            q = q.where(AuditEventRow.actor_id == actor_id)
        if resource_type:
            q = q.where(AuditEventRow.resource_type == resource_type)
        if resource_id:
            q = q.where(AuditEventRow.resource_id == resource_id)
        if action:
            q = q.where(AuditEventRow.action == action)
        if date_from:
            q = q.where(AuditEventRow.occurred_at >= date_from)
        if date_to:
            q = q.where(AuditEventRow.occurred_at <= date_to)
        total = (await self.s.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
        rows = (await self.s.execute(q.order_by(AuditEventRow.seq.desc()).limit(limit).offset(offset))).scalars().all()
        return rows, total

    async def iter_chain(
        self, tenant_id: UUID | None, after_seq: int = 0, batch: int = 1000
    ) -> AsyncIterator[dict[str, Any]]:
        last = after_seq
        while True:
            q = select(AuditEventRow).where(AuditEventRow.seq > last)
            q = (
                q.where(AuditEventRow.tenant_id == tenant_id)
                if tenant_id
                else q.where(AuditEventRow.tenant_id.is_(None))
            )
            rows = (await self.s.execute(q.order_by(AuditEventRow.seq).limit(batch))).scalars().all()
            if not rows:
                return
            for r in rows:
                yield r.to_dict()
            last = rows[-1].seq
