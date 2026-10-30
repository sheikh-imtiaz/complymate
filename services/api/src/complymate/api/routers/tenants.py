from __future__ import annotations

import re
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile

from complymate.api.deps import Ctx, authenticated, require
from complymate.db.models import ImpersonationSession, Membership, Tenant
from complymate.db.repositories.programs import ProgramRepo
from complymate.db.repositories.tenants import TenantRepo
from complymate.db.repositories.users import UserRepo
from complymate.db.session import apply_context
from complymate.domain.audit.events import Action
from complymate.domain.billing.plans import get_plan
from complymate.domain.errors import Conflict, NotFound, ValidationFailed
from complymate.domain.platform.feature_flags import resolve
from complymate.domain.rbac.permissions import P
from complymate.domain.tenants.designated_services import QUESTIONS, check_applicability
from complymate.schemas.common import Ok
from complymate.schemas.tenants import (
    AmlcoIn,
    ApplicabilityIn,
    ApplicabilityOut,
    ImpersonationConsentIn,
    ServiceQuestionOut,
    SettingsOut,
    SettingsUpdate,
    TenantCreate,
    TenantOut,
    TenantUpdate,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60] or "firm"


@router.get("/designated-services", response_model=list[ServiceQuestionOut])
async def designated_services() -> list[ServiceQuestionOut]:
    return [ServiceQuestionOut(**q.__dict__) for q in QUESTIONS]


@router.post("/check-applicability", response_model=ApplicabilityOut)
async def applicability(body: ApplicabilityIn) -> ApplicabilityOut:
    return ApplicabilityOut(**check_applicability(body.jurisdiction, body.services).__dict__)


@router.post("", response_model=TenantOut, status_code=201)
async def create_tenant(body: TenantCreate, ctx: Ctx = Depends(authenticated)) -> Tenant:
    """Sign-up step: the signed-in user creates their firm and becomes its owner."""
    if ctx.principal.api_key_id or ctx.principal.impersonation_id:
        raise ValidationFailed("cannot create a firm with this credential")
    tenant_id = uuid.uuid4()
    await apply_context(ctx.session, tenant_id, user_id=ctx.user_id)
    repo = TenantRepo(ctx.session)
    slug = _slugify(body.name)
    if await repo.slug_exists(slug):
        slug = f"{slug}-{secrets.token_hex(3)}"
    result = check_applicability(body.jurisdiction, body.services)
    tenant = Tenant(
        id=tenant_id,
        name=body.name,
        slug=slug,
        jurisdiction=body.jurisdiction,
        entity_type=body.entity_type,
        abn=body.abn,
        nzbn=body.nzbn,
        services=body.services,
        size=body.size,
        status="trial",
        tranche2_applies=result.applies,
        plan_code=body.plan_code,
    )
    await repo.create(tenant, body.plan_code)
    owner_role = await UserRepo(ctx.session).role_by_key("owner")
    assert owner_role is not None
    ctx.session.add(Membership(tenant_id=tenant_id, user_id=ctx.user_id, role_id=owner_role.id))
    await ProgramRepo(ctx.session).ensure(tenant_id, ctx.user_id)
    await ctx.audit.record(
        ctx.audit_ctx,
        Action.CREATE,
        "tenant",
        tenant_id,
        tenant_id=tenant_id,
        after={"name": body.name, "jurisdiction": body.jurisdiction, "plan": body.plan_code},
    )
    return tenant


@router.get("/current", response_model=TenantOut)
async def current(ctx: Ctx = Depends(require(P.FIRM_READ))) -> Tenant:
    tenant = await TenantRepo(ctx.session).get(ctx.tenant_id)
    if tenant is None:
        raise NotFound("firm not found")
    return tenant


@router.patch("/current", response_model=TenantOut)
async def update_current(body: TenantUpdate, ctx: Ctx = Depends(require(P.FIRM_UPDATE))) -> Tenant:
    tenant = await TenantRepo(ctx.session).get(ctx.tenant_id)
    assert tenant is not None
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(tenant, k) for k in changes}
    for k, v in changes.items():
        setattr(tenant, k, v)
    if "services" in changes:
        tenant.tranche2_applies = check_applicability(tenant.jurisdiction, tenant.services).applies
    await ctx.record(Action.UPDATE, "tenant", tenant.id, before=before, after=changes)
    return tenant


@router.post("/current/amlco", response_model=TenantOut)
async def nominate_amlco(body: AmlcoIn, ctx: Ctx = Depends(require(P.FIRM_UPDATE))) -> Tenant:
    users = UserRepo(ctx.session)
    found = await users.membership(ctx.tenant_id, body.user_id)
    if found is None:
        raise NotFound("user is not a member of this firm")
    tenant = await TenantRepo(ctx.session).get(ctx.tenant_id)
    assert tenant is not None
    before = {"amlco_user_id": str(tenant.amlco_user_id) if tenant.amlco_user_id else None}
    tenant.amlco_user_id = body.user_id
    membership, role = found
    if role.key not in ("owner", "amlco"):
        amlco_role = await users.role_by_key("amlco")
        assert amlco_role is not None
        membership.role_id = amlco_role.id
        await ctx.record(
            Action.ROLE_CHANGE, "membership", membership.id, before={"role": role.key}, after={"role": "amlco"}
        )
    await ctx.record(
        Action.UPDATE,
        "tenant",
        tenant.id,
        before=before,
        after={"amlco_user_id": str(body.user_id)},
        reason="AML/CTF compliance officer nominated",
    )
    return tenant


@router.get("/current/settings", response_model=SettingsOut)
async def get_settings(ctx: Ctx = Depends(require(P.SETTINGS_READ))) -> object:
    return await TenantRepo(ctx.session).settings(ctx.tenant_id)


@router.patch("/current/settings", response_model=SettingsOut)
async def update_settings(body: SettingsUpdate, ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))) -> object:
    import ipaddress

    repo = TenantRepo(ctx.session)
    settings = await repo.settings(ctx.tenant_id)
    tenant = await repo.get(ctx.tenant_id)
    plan = get_plan(tenant.plan_code if tenant else "solo")
    changes = body.model_dump(exclude_unset=True)
    if changes.get("ip_allow_list"):
        if "ip_allow_list" not in plan.features:
            raise ValidationFailed("IP allow-list is available on the Practice plan")
        for net in changes["ip_allow_list"]:
            try:
                ipaddress.ip_network(net, strict=False)
            except ValueError as exc:
                raise ValidationFailed(f"invalid network {net}") from exc
        if ctx.ip and not any(
            ipaddress.ip_address(ctx.ip) in ipaddress.ip_network(n, strict=False) for n in changes["ip_allow_list"]
        ):
            raise Conflict("your current IP address is not in the list; you would lock yourself out")
    if ctx.principal.role_key != "owner":
        # AMLCO can update settings, but security controls belong to the owner.
        for owner_only in ("mfa_required", "ip_allow_list", "allow_support_impersonation", "retention_years"):
            if owner_only in changes:
                raise ValidationFailed(f"only the firm owner can change {owner_only}")
    before = {k: getattr(settings, k) for k in changes}
    for k, v in changes.items():
        setattr(settings, k, v)
    await ctx.record(Action.UPDATE, "tenant_settings", ctx.tenant_id, before=before, after=changes)
    return settings


@router.post("/current/branding/logo", response_model=SettingsOut)
async def upload_logo(file: UploadFile = File(...), ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))) -> object:
    data = await file.read()
    if len(data) > 512_000 or not (data.startswith(b"\x89PNG") or data.startswith(b"\xff\xd8\xff")):
        raise ValidationFailed("logo must be a PNG or JPEG under 500 KB")
    key = f"{ctx.tenant_id}/branding/logo-{uuid.uuid4().hex[:8]}"
    await ctx.container.storage.put_object(
        ctx.container.settings.exports_bucket, key, data, file.content_type or "image/png"
    )
    settings = await TenantRepo(ctx.session).settings(ctx.tenant_id)
    settings.branding = {**(settings.branding or {}), "logo_key": key}
    await ctx.record(Action.UPDATE, "tenant_settings", ctx.tenant_id, after={"branding.logo_key": key})
    return settings


@router.get("/current/flags")
async def flags(ctx: Ctx = Depends(require(P.FIRM_READ))) -> dict[str, bool]:
    g, t = await TenantRepo(ctx.session).flags(ctx.tenant_id)
    return resolve(g, t)


@router.get("/current/impersonation-requests")
async def impersonation_requests(ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))) -> list[dict[str, object]]:
    from sqlalchemy import select

    rows = (
        (
            await ctx.session.execute(
                select(ImpersonationSession)
                .where(ImpersonationSession.tenant_id == ctx.tenant_id)
                .order_by(ImpersonationSession.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    return [r.to_dict() for r in rows]


@router.post("/current/impersonation-requests/{request_id}/consent", response_model=Ok)
async def consent_impersonation(
    request_id: UUID, body: ImpersonationConsentIn, ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))
) -> Ok:
    if ctx.principal.role_key != "owner":
        raise ValidationFailed("only the firm owner can approve support access")
    imp = await ctx.session.get(ImpersonationSession, request_id)
    if imp is None or imp.tenant_id != ctx.tenant_id:
        raise NotFound("request not found")
    if imp.consented_at or imp.ended_at:
        raise Conflict("request already decided")
    now = datetime.now(UTC)
    if body.approve:
        imp.consented_by = ctx.user_id
        imp.consented_at = now
        imp.expires_at = now + timedelta(minutes=imp.duration_minutes)
    else:
        imp.ended_at = now
    await ctx.record(
        Action.APPROVE if body.approve else Action.REJECT,
        "impersonation_session",
        imp.id,
        after={"minutes": imp.duration_minutes},
        reason=imp.reason,
    )
    return Ok()
