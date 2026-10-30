"""Audit service: builds events, chains them and appends through a repository (INSERT only)."""

from __future__ import annotations

import uuid
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import UUID

import structlog

from complymate.domain.audit.events import SECURITY_ACTIONS, AuditContext, AuditEvent
from complymate.domain.audit.hash_chain import compute_hash
from complymate.observability import metrics

log = structlog.get_logger("security")

_REDACT_KEYS = {"password", "token", "secret", "key_hash", "token_hash", "encrypted_data_key"}


class AuditRepository(Protocol):
    async def lock_tenant_chain(self, tenant_id: UUID | None) -> None: ...

    async def last_hash(self, tenant_id: UUID | None) -> str | None: ...

    async def insert(self, event: AuditEvent) -> None: ...


def _clean(data: dict[str, Any] | None) -> dict[str, Any] | None:
    if data is None:
        return None
    return {k: ("[redacted]" if k in _REDACT_KEYS else v) for k, v in data.items()}


class AuditService:
    def __init__(self, repo: AuditRepository) -> None:
        self.repo = repo

    async def record(
        self,
        ctx: AuditContext,
        action: str,
        resource_type: str,
        resource_id: str | UUID | None,
        *,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
        reason: str | None = None,
        ai: dict[str, Any] | None = None,
        tenant_id: UUID | None = None,
    ) -> AuditEvent:
        tid = tenant_id if tenant_id is not None else ctx.tenant_id
        event = AuditEvent(
            id=uuid.uuid4(),
            tenant_id=tid,
            actor_id=ctx.actor_id,
            actor_role=ctx.actor_role,
            action=str(action),
            resource_type=resource_type,
            resource_id=str(resource_id) if resource_id is not None else None,
            occurred_at=datetime.now(UTC),
            before=_clean(before),
            after=_clean(after),
            reason=reason,
            ip=ctx.ip,
            user_agent=(ctx.user_agent or "")[:400] or None,
            request_id=ctx.request_id,
            ai=ai,
        )
        # Serialise writers per tenant so the chain stays linear.
        await self.repo.lock_tenant_chain(tid)
        event.prev_hash = await self.repo.last_hash(tid)
        event.hash = compute_hash(event.prev_hash, asdict(event))
        await self.repo.insert(event)
        if action in SECURITY_ACTIONS:
            # Security alert channel: CloudWatch metric filter / Azure alert rule on this event name.
            log.warning(
                "security_event",
                category=str(action),
                resource_type=resource_type,
                actor_role=ctx.actor_role,
                tenant_id=str(tid) if tid else None,
            )
            metrics.security_event(str(action))
        return event
