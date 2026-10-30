from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.config import Settings
from complymate.db.models import LlmCall
from complymate.observability import metrics


def cost_usd(settings: Settings, input_tokens: int, output_tokens: int) -> Decimal:
    cost = (
        input_tokens * settings.llm_input_cost_per_mtok / 1e6 + output_tokens * settings.llm_output_cost_per_mtok / 1e6
    )
    return Decimal(str(round(cost, 5)))


async def record(
    session: AsyncSession,
    settings: Settings,
    *,
    tenant_id: UUID | None,
    purpose: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: int,
) -> Decimal:
    cost = cost_usd(settings, input_tokens, output_tokens)
    session.add(
        LlmCall(
            tenant_id=tenant_id,
            purpose=purpose,
            model=model,
            prompt_version=settings.prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
        )
    )
    metrics.llm_usage(str(tenant_id), purpose, input_tokens, output_tokens, float(cost))
    return cost
