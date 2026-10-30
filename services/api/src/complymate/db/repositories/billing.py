from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import StripeEvent, Subscription, UsageCounter
from complymate.domain.billing.usage import period


class BillingRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def increment(self, tenant_id: UUID, metric: str, by: int = 1) -> int:
        stmt = (
            insert(UsageCounter)
            .values(tenant_id=tenant_id, period=period(), metric=metric, value=by)
            .on_conflict_do_update(
                index_elements=["tenant_id", "period", "metric"], set_={"value": UsageCounter.value + by}
            )
            .returning(UsageCounter.value)
        )
        return int((await self.s.execute(stmt)).scalar_one())

    async def used(self, tenant_id: UUID, metric: str) -> int:
        stmt = select(UsageCounter.value).where(
            UsageCounter.tenant_id == tenant_id, UsageCounter.period == period(), UsageCounter.metric == metric
        )
        return int((await self.s.execute(stmt)).scalar_one_or_none() or 0)

    async def subscription(self, tenant_id: UUID) -> Subscription | None:
        return (
            await self.s.execute(select(Subscription).where(Subscription.tenant_id == tenant_id))
        ).scalar_one_or_none()

    async def by_customer(self, customer_id: str) -> Subscription | None:
        stmt = select(Subscription).where(Subscription.stripe_customer_id == customer_id)
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def event_seen(self, event_id: str, type_: str) -> bool:
        stmt = insert(StripeEvent).values(id=event_id, type=type_).on_conflict_do_nothing().returning(StripeEvent.id)
        inserted = (await self.s.execute(stmt)).scalar_one_or_none()
        return inserted is None
