from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.db.models import ApiKey, Tenant
from complymate.domain.api_keys.service import assert_subset, generate
from complymate.domain.audit.events import Action
from complymate.domain.billing.limits import has_feature
from complymate.domain.billing.plans import get_plan
from complymate.domain.errors import NotFound, ValidationFailed
from complymate.domain.rbac.permissions import P
from complymate.schemas.api_keys import ApiKeyCreate, ApiKeyCreated, ApiKeyOut
from complymate.schemas.common import Ok

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


@router.get("", response_model=list[ApiKeyOut])
async def list_keys(ctx: Ctx = Depends(require(P.SETTINGS_READ))) -> list[ApiKey]:
    stmt = select(ApiKey).where(ApiKey.tenant_id == ctx.tenant_id).order_by(ApiKey.created_at.desc())
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("", response_model=ApiKeyCreated, status_code=201)
async def create_key(body: ApiKeyCreate, ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))) -> ApiKeyCreated:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    if not has_feature(get_plan(tenant.plan_code if tenant else "solo"), "api_keys"):
        raise ValidationFailed("API keys are available on the Practice plan")
    assert_subset(set(body.permissions), ctx.principal.permissions)
    full, prefix, key_hash = generate()
    key = ApiKey(
        tenant_id=ctx.tenant_id,
        name=body.name,
        prefix=prefix,
        key_hash=key_hash,
        permissions=sorted(body.permissions),
        created_by=ctx.user_id,
        expires_at=body.expires_at,
    )
    ctx.session.add(key)
    await ctx.session.flush()
    await ctx.record(Action.CREATE, "api_key", key.id, after={"name": body.name, "permissions": key.permissions})
    out = ApiKeyCreated.model_validate({**ApiKeyOut.model_validate(key).model_dump(), "key": full})
    return out


@router.delete("/{key_id}", response_model=Ok)
async def revoke_key(key_id: UUID, ctx: Ctx = Depends(require(P.SETTINGS_UPDATE))) -> Ok:
    key = await ctx.session.get(ApiKey, key_id)
    if key is None:
        raise NotFound("API key not found")
    key.revoked_at = datetime.now(UTC)
    await ctx.record(Action.DELETE, "api_key", key.id)
    return Ok()
