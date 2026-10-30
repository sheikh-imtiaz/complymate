from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select, text

from complymate.api.deps import Ctx, authenticated, require
from complymate.application.notify import notify
from complymate.application.usage import meter
from complymate.db.models import Invitation, Membership
from complymate.db.repositories.users import UserRepo
from complymate.db.session import apply_context
from complymate.domain.audit.events import Action
from complymate.domain.errors import Conflict, Forbidden, NotFound, ValidationFailed
from complymate.domain.invitations.service import expiry, hash_token, is_usable, new_token
from complymate.domain.rbac.permissions import P
from complymate.ports.queue import QueueName
from complymate.schemas.common import Ok
from complymate.schemas.invitations import AcceptIn, InvitationCreate, InvitationCreated, InvitationOut

router = APIRouter(prefix="/invitations", tags=["invitations"])


@router.get("", response_model=list[InvitationOut])
async def list_invitations(ctx: Ctx = Depends(require(P.USER_READ))) -> list[Invitation]:
    stmt = select(Invitation).where(Invitation.tenant_id == ctx.tenant_id).order_by(Invitation.created_at.desc())
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("", response_model=InvitationCreated, status_code=201)
async def invite(body: InvitationCreate, ctx: Ctx = Depends(require(P.USER_CREATE))) -> InvitationCreated:
    users = UserRepo(ctx.session)
    role = await users.role_by_key(body.role_key, ctx.tenant_id)
    if role is None:
        raise NotFound("role not found")
    if role.key == "owner" and ctx.principal.role_key != "owner":
        raise Forbidden("only an owner can invite another owner")
    existing = await users.by_email(body.email)
    if existing and await users.membership(ctx.tenant_id, existing.id):
        raise Conflict("this person is already a member")
    if role.key != "advisor":
        await meter(ctx.session, ctx.tenant_id, "users")  # seats: hard limit by plan
    token, token_hash = new_token()
    inv = Invitation(
        tenant_id=ctx.tenant_id,
        email=body.email.lower(),
        full_name=body.full_name,
        role_id=role.id,
        token_hash=token_hash,
        invited_by=ctx.user_id,
        expires_at=expiry(),
    )
    ctx.session.add(inv)
    await ctx.session.flush()
    await ctx.container.identity.invite_user(body.email, body.full_name)
    accept_url = f"{ctx.container.settings.web_base_url}/accept-invite?token={token}"
    await ctx.container.queue.send(
        QueueName.NOTIFICATIONS,
        {
            "task": "send_invite_email",
            "payload": {"tenant_id": str(ctx.tenant_id), "invitation_id": str(inv.id), "accept_url": accept_url},
        },
    )
    await ctx.record(Action.INVITE, "invitation", inv.id, after={"email": body.email, "role": role.key})
    out = InvitationCreated.model_validate(inv)
    out.accept_url = accept_url if ctx.container.settings.is_local else None
    return out


@router.delete("/{invitation_id}", response_model=Ok)
async def revoke(invitation_id: UUID, ctx: Ctx = Depends(require(P.USER_DELETE))) -> Ok:
    inv = await ctx.session.get(Invitation, invitation_id)
    if inv is None:
        raise NotFound("invitation not found")
    inv.revoked_at = datetime.now(UTC)
    await ctx.record(Action.DELETE, "invitation", inv.id)
    return Ok()


@router.post("/accept", response_model=Ok)
async def accept(body: AcceptIn, ctx: Ctx = Depends(authenticated)) -> Ok:
    token_hash = hash_token(body.token)
    tenant_id = (
        await ctx.session.execute(text("SELECT app_invitation_tenant(:h)"), {"h": token_hash})
    ).scalar_one_or_none()
    if tenant_id is None:
        raise NotFound("invitation not found")
    await apply_context(ctx.session, tenant_id, user_id=ctx.user_id)
    inv = (await ctx.session.execute(select(Invitation).where(Invitation.token_hash == token_hash))).scalar_one()
    if not is_usable(inv.expires_at, inv.accepted_at, inv.revoked_at):
        raise ValidationFailed("invitation has expired or was already used")
    if inv.email.lower() != ctx.principal.email.lower():
        raise Forbidden("this invitation was sent to a different email address")
    if await UserRepo(ctx.session).membership(tenant_id, ctx.user_id) is None:
        ctx.session.add(Membership(tenant_id=tenant_id, user_id=ctx.user_id, role_id=inv.role_id))
    inv.accepted_at = datetime.now(UTC)
    await ctx.audit.record(
        ctx.audit_ctx,
        Action.CREATE,
        "membership",
        ctx.user_id,
        tenant_id=tenant_id,
        after={"invitation_id": str(inv.id)},
    )
    if inv.invited_by:
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=tenant_id,
            user_ids=[inv.invited_by],
            kind="invite_accepted",
            title=f"{ctx.principal.email} joined your firm",
            link="/admin/users",
        )
    return Ok()
