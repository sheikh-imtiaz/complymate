"""Share an item with an External Advisor until an expiry date. The advisor gets an `advisor` membership that
expires with the share and can only read shared items (RBAC `:shared` scope + shares table)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.application.notify import notify
from complymate.db.models import Membership, Share
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.collaboration.shares import validate
from complymate.domain.errors import Conflict, NotFound
from complymate.domain.rbac.permissions import P
from complymate.schemas.common import Ok
from complymate.schemas.shares import ShareIn, ShareOut

router = APIRouter(prefix="/shares", tags=["shares"])


@router.get("", response_model=list[ShareOut])
async def list_shares(
    resource_type: str | None = None, resource_id: str | None = None, ctx: Ctx = Depends(require(P.SHARE_CREATE))
) -> list[object]:
    stmt = select(Share).order_by(Share.created_at.desc())
    if resource_type:
        stmt = stmt.where(Share.resource_type == resource_type)
    if resource_id:
        stmt = stmt.where(Share.resource_id == resource_id)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("", response_model=ShareOut, status_code=201)
async def create_share(body: ShareIn, ctx: Ctx = Depends(require(P.SHARE_CREATE))) -> object:
    validate(body.resource_type, body.expires_at)
    users = UserRepo(ctx.session)
    sub = await ctx.container.identity.invite_user(body.advisor_email, body.advisor_name)
    advisor = await users.get_or_create(sub, body.advisor_email, body.advisor_name)
    found = await users.membership(ctx.tenant_id, advisor.id)
    advisor_role = await users.role_by_key("advisor")
    assert advisor_role is not None
    if found is None:
        ctx.session.add(
            Membership(tenant_id=ctx.tenant_id, user_id=advisor.id, role_id=advisor_role.id, expires_at=body.expires_at)
        )
    else:
        membership, role = found
        if role.key != "advisor":
            raise Conflict("this person is already a firm member; no share is needed")
        membership.expires_at = max(membership.expires_at or body.expires_at, body.expires_at)
        membership.status = "active"
    share = Share(
        tenant_id=ctx.tenant_id,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
        grantee_user_id=advisor.id,
        granted_by=ctx.user_id,
        expires_at=body.expires_at,
    )
    ctx.session.add(share)
    await ctx.session.flush()
    await notify(
        ctx.session,
        ctx.container,
        tenant_id=ctx.tenant_id,
        user_ids=[advisor.id],
        kind="invite",
        title="A firm shared an item with you",
        link=f"/{body.resource_type.replace('_', '-')}s/{body.resource_id}",
    )
    await ctx.record(
        Action.SHARE,
        body.resource_type,
        body.resource_id,
        after={"advisor": body.advisor_email, "expires_at": body.expires_at.isoformat()},
    )
    return share


@router.delete("/{share_id}", response_model=Ok)
async def revoke_share(share_id: UUID, ctx: Ctx = Depends(require(P.SHARE_CREATE))) -> Ok:
    share = await ctx.session.get(Share, share_id)
    if share is None:
        raise NotFound("share not found")
    share.revoked_at = datetime.now(UTC)
    await ctx.record(Action.DELETE, "share", share.id)
    return Ok()
