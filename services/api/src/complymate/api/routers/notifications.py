from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select, update

from complymate.api.deps import Ctx, require
from complymate.db.models import Notification
from complymate.domain.errors import NotFound
from complymate.domain.rbac.permissions import P
from complymate.schemas.common import Ok
from complymate.schemas.notifications import NotificationOut

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    unread_only: bool = False, ctx: Ctx = Depends(require(P.NOTIFICATION_READ))
) -> list[object]:
    stmt = select(Notification).where(Notification.user_id == ctx.user_id)
    if unread_only:
        stmt = stmt.where(Notification.read_at.is_(None))
    return list((await ctx.session.execute(stmt.order_by(Notification.created_at.desc()).limit(100))).scalars().all())


@router.get("/unread-count")
async def unread_count(ctx: Ctx = Depends(require(P.NOTIFICATION_READ))) -> dict[str, int]:
    stmt = select(func.count()).where(Notification.user_id == ctx.user_id, Notification.read_at.is_(None))
    return {"count": (await ctx.session.execute(stmt)).scalar_one()}


@router.post("/{notification_id}/read", response_model=Ok)
async def mark_read(notification_id: UUID, ctx: Ctx = Depends(require(P.NOTIFICATION_READ))) -> Ok:
    n = await ctx.session.get(Notification, notification_id)
    if n is None or n.user_id != ctx.user_id:
        raise NotFound("notification not found")
    n.read_at = datetime.now(UTC)
    return Ok()


@router.post("/read-all", response_model=Ok)
async def mark_all_read(ctx: Ctx = Depends(require(P.NOTIFICATION_READ))) -> Ok:
    await ctx.session.execute(
        update(Notification)
        .where(Notification.user_id == ctx.user_id, Notification.read_at.is_(None))
        .values(read_at=datetime.now(UTC))
    )
    return Ok()
