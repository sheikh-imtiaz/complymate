from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Tenant
from complymate.db.repositories.billing import BillingRepo
from complymate.domain.billing import limits
from complymate.domain.billing.plans import get_plan


async def meter(session: AsyncSession, tenant_id: UUID, metric: str, by: int = 1) -> limits.LimitCheck:
    """Enforce the hard limit, then count. Returns the check so callers can surface soft warnings."""
    tenant = await session.get(Tenant, tenant_id)
    plan = get_plan(tenant.plan_code if tenant else "solo")
    repo = BillingRepo(session)
    used = await repo.used(tenant_id, metric)
    check = limits.enforce(plan, metric, used, by)
    await repo.increment(tenant_id, metric, by)
    return check
