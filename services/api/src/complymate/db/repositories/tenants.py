from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import FeatureFlag, Membership, Subscription, Tenant, TenantSettings, UsageCounter
from complymate.domain.billing.plans import TRIAL_DAYS


class TenantRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def get(self, tenant_id: UUID) -> Tenant | None:
        return await self.s.get(Tenant, tenant_id)

    async def settings(self, tenant_id: UUID) -> TenantSettings:
        settings = await self.s.get(TenantSettings, tenant_id)
        if settings is None:
            settings = TenantSettings(tenant_id=tenant_id)
            self.s.add(settings)
            await self.s.flush()
        return settings

    async def create(self, tenant: Tenant, plan_code: str = "solo") -> Tenant:
        self.s.add(tenant)
        await self.s.flush()
        self.s.add(TenantSettings(tenant_id=tenant.id))
        self.s.add(
            Subscription(
                tenant_id=tenant.id,
                plan_code=plan_code,
                status="trialing",
                seats=1,
                trial_ends_at=datetime.now(UTC) + timedelta(days=TRIAL_DAYS),
            )
        )
        await self.s.flush()
        return tenant

    async def slug_exists(self, slug: str) -> bool:
        # RLS hides other tenants, so ask a SECURITY DEFINER function.
        return bool((await self.s.execute(text("SELECT app_slug_taken(:s)"), {"s": slug})).scalar_one())

    async def list_all(self, status: str | None = None, q: str | None = None) -> Sequence[Tenant]:
        stmt = select(Tenant).order_by(Tenant.created_at.desc())
        if status:
            stmt = stmt.where(Tenant.status == status)
        if q:
            stmt = stmt.where(Tenant.name.ilike(f"%{q}%"))
        return (await self.s.execute(stmt.limit(500))).scalars().all()

    async def member_count(self, tenant_id: UUID) -> int:
        stmt = select(func.count()).where(Membership.tenant_id == tenant_id, Membership.status == "active")
        return (await self.s.execute(stmt)).scalar_one()

    async def subscription(self, tenant_id: UUID) -> Subscription | None:
        return (
            await self.s.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        ).scalar_one_or_none()

    async def usage(self, tenant_id: UUID, period: str) -> dict[str, int]:
        rows = await self.s.execute(
            select(UsageCounter.metric, UsageCounter.value).where(
                UsageCounter.tenant_id == tenant_id, UsageCounter.period == period
            )
        )
        return {m: int(v) for m, v in rows.all()}

    async def flags(self, tenant_id: UUID | None) -> tuple[dict[str, bool], dict[str, bool]]:
        rows = (await self.s.execute(select(FeatureFlag))).scalars().all()
        global_flags = {f.key: f.enabled for f in rows if f.tenant_id is None}
        tenant_flags = {f.key: f.enabled for f in rows if tenant_id and f.tenant_id == tenant_id}
        return global_flags, tenant_flags
