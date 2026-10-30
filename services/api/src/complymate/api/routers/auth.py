from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends

from complymate.api.deps import Ctx, authenticated
from complymate.container import get_container
from complymate.db.repositories.tenants import TenantRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden
from complymate.domain.platform.feature_flags import resolve
from complymate.schemas.auth import DevLoginIn, MembershipOut, MeOut, TokenOut
from complymate.schemas.common import Ok

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/dev-login", response_model=TokenOut)
async def dev_login(body: DevLoginIn) -> TokenOut:
    """Local development only: sign in as any user without a password."""
    container = get_container()
    if not container.settings.is_local:
        raise Forbidden("dev login is disabled")
    from complymate.adapters.local.dev_identity import DevIdentity  # local adapter, never loaded on AWS/Azure

    identity = container.identity
    assert isinstance(identity, DevIdentity)
    maker = await container.sessionmaker()
    async with maker() as session:
        user = await UserRepo(session).by_email(body.email)
    sub = user.external_sub if user else await identity.invite_user(body.email)
    return TokenOut(access_token=identity.issue_token(sub, body.email, user.full_name if user else None))


@router.get("/me", response_model=MeOut)
async def me(ctx: Ctx = Depends(authenticated)) -> MeOut:
    p = ctx.principal
    memberships = await UserRepo(ctx.session).memberships(p.user_id) if p.api_key_id is None else []
    flags: dict[str, bool] = {}
    if p.tenant_id:
        g, t = await TenantRepo(ctx.session).flags(p.tenant_id)
        flags = resolve(g, t)
    step_up_until = (
        p.auth_time + timedelta(seconds=ctx.container.settings.step_up_mfa_seconds)
        if p.auth_time and p.mfa_verified
        else None
    )
    return MeOut(
        user_id=p.user_id,
        email=p.email,
        full_name=ctx.user.full_name if ctx.user else None,
        platform_role=p.platform_role,
        memberships=[MembershipOut(**m) for m in memberships],
        tenant_id=p.tenant_id,
        role_key=p.role_key,
        permissions=sorted(p.permissions),
        mfa_verified=p.mfa_verified,
        auth_time=p.auth_time,
        step_up_valid_until=step_up_until,
        impersonation_id=p.impersonation_id,
        feature_flags=flags,
    )


@router.post("/session", response_model=Ok)
async def session_started(ctx: Ctx = Depends(authenticated)) -> Ok:
    """Called by the web app right after sign-in: records the login in the audit log."""
    if ctx.user:
        ctx.user.last_login_at = datetime.now(UTC)
        ctx.user.mfa_enrolled = ctx.user.mfa_enrolled or ctx.principal.mfa_verified
    if ctx.principal.tenant_id:
        await ctx.record(Action.LOGIN, "user", ctx.user_id, after={"mfa": ctx.principal.mfa_verified})
    return Ok()
