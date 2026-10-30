from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from complymate.api.deps import Ctx, require
from complymate.db.repositories.audit import AuditRepo
from complymate.domain.audit.events import Action
from complymate.domain.audit.hash_chain import verify_chain
from complymate.domain.rbac.permissions import P
from complymate.domain.reports.registers import to_csv
from complymate.schemas.audit import AuditEventOut, ChainStatus
from complymate.schemas.common import Page

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=Page[AuditEventOut])
async def search(
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    ctx: Ctx = Depends(require(P.AUDIT_READ)),
) -> Page[AuditEventOut]:
    rows, total = await AuditRepo(ctx.session).search(
        ctx.tenant_id,
        actor_id=actor_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )
    return Page(items=[AuditEventOut.model_validate(r) for r in rows], total=total, limit=limit, offset=offset)


@router.get("/export")
async def export(
    actor_id: UUID | None = None,
    resource_type: str | None = None,
    action: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    ctx: Ctx = Depends(require(P.AUDIT_EXPORT)),
) -> Response:
    rows, _ = await AuditRepo(ctx.session).search(
        ctx.tenant_id,
        actor_id=actor_id,
        resource_type=resource_type,
        action=action,
        date_from=date_from,
        date_to=date_to,
        limit=100_000,
    )
    cols = [
        "seq",
        "occurred_at",
        "actor_id",
        "actor_role",
        "action",
        "resource_type",
        "resource_id",
        "reason",
        "ip",
        "request_id",
        "prev_hash",
        "hash",
    ]
    await ctx.record(Action.EXPORT, "audit_log", None, after={"rows": len(rows)})
    return Response(
        to_csv([{c: getattr(r, c) for c in cols} for r in rows], cols),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="audit-trail.csv"'},
    )


@router.get("/verify", response_model=ChainStatus)
async def verify(ctx: Ctx = Depends(require(P.AUDIT_READ))) -> ChainStatus:
    events = [e async for e in AuditRepo(ctx.session).iter_chain(ctx.tenant_id)]
    result = verify_chain(events)
    return ChainStatus(ok=result.ok, checked=result.checked, broken_at_id=result.broken_at_id, reason=result.reason)
