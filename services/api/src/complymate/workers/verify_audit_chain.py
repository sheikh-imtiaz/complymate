"""Nightly audit hash-chain verification for every tenant and the platform chain. A break raises an alert
(metric AuditChainBreak → CloudWatch alarm → SNS / Azure alert) and is recorded."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from complymate.db.models import ChainVerification
from complymate.db.repositories.audit import AuditRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.hash_chain import verify_chain
from complymate.observability import metrics
from complymate.workers._common import active_tenant_ids

log = structlog.get_logger("security")


async def _verify(tenant_id: UUID | None) -> bool:
    async with tenant_session(tenant_id, platform=tenant_id is None) as session:
        events = [e async for e in AuditRepo(session).iter_chain(tenant_id)]
        result = verify_chain(events)
        session.add(
            ChainVerification(
                tenant_id=tenant_id,
                ok=result.ok,
                checked=result.checked,
                broken_at_id=result.broken_at_id,
                reason=result.reason,
            )
        )
    if not result.ok:
        metrics.audit_chain_break(str(tenant_id))
        log.error(
            "security_event", category="audit_chain_break", tenant_id=str(tenant_id), broken_at=result.broken_at_id
        )
    return result.ok


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    broken = []
    for tenant_id in [None, *await active_tenant_ids()]:
        if not await _verify(tenant_id):
            broken.append(str(tenant_id))
    return {"broken": broken}
