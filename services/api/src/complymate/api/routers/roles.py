from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select

from complymate.api.deps import Ctx, require
from complymate.db.models import Membership, Role, RolePermission, Tenant
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.billing.limits import has_feature
from complymate.domain.billing.plans import get_plan
from complymate.domain.errors import Conflict, NotFound, ValidationFailed
from complymate.domain.rbac.permissions import ALL_PERMISSIONS, P
from complymate.domain.rbac.roles import TENANT_ROLES
from complymate.schemas.common import Ok
from complymate.schemas.roles import RoleCreate, RoleOut, RoleUpdate

router = APIRouter(prefix="/roles", tags=["roles"])


def _valid_permissions(perms: list[str]) -> list[str]:
    base = {p.rsplit(":", 1)[0] if p.endswith((":own", ":shared")) else p for p in perms}
    invalid = sorted(p for p in base if p not in ALL_PERMISSIONS or p.startswith("platform:"))
    if invalid:
        raise ValidationFailed(f"unknown permissions: {invalid}")
    return sorted(set(perms))


@router.get("/permissions")
async def permission_catalog(ctx: Ctx = Depends(require(P.USER_READ))) -> list[str]:
    return sorted(p for p in ALL_PERMISSIONS if not p.startswith("platform:"))


@router.get("", response_model=list[RoleOut])
async def list_roles(ctx: Ctx = Depends(require(P.USER_READ))) -> list[RoleOut]:
    users = UserRepo(ctx.session)
    return [
        RoleOut(
            id=r.id,
            key=r.key,
            name=r.name,
            description=r.description,
            is_system=r.is_system,
            permissions=sorted(await users.role_permissions(r.id)),
        )
        for r in await users.roles(ctx.tenant_id)
    ]


async def _require_custom_roles(ctx: Ctx) -> None:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    if not has_feature(get_plan(tenant.plan_code if tenant else "solo"), "custom_roles"):
        raise ValidationFailed("custom roles are available on the Practice plan")


@router.post("", response_model=RoleOut, status_code=201)
async def create_role(body: RoleCreate, ctx: Ctx = Depends(require(P.USER_CREATE))) -> RoleOut:
    await _require_custom_roles(ctx)
    if body.key in TENANT_ROLES:
        raise Conflict("that key is reserved for a system role")
    if body.base_role_key not in TENANT_ROLES:
        raise ValidationFailed("base role must be a system role")
    perms = _valid_permissions(body.permissions)
    role = Role(
        tenant_id=ctx.tenant_id,
        key=body.key,
        name=body.name,
        description=body.description,
        is_system=False,
        base_role_key=body.base_role_key,
    )
    ctx.session.add(role)
    await ctx.session.flush()
    ctx.session.add_all(RolePermission(role_id=role.id, permission=p, tenant_id=ctx.tenant_id) for p in perms)
    await ctx.record(Action.PERMISSION_CHANGE, "role", role.id, after={"key": body.key, "permissions": perms})
    return RoleOut(
        id=role.id, key=role.key, name=role.name, description=role.description, is_system=False, permissions=perms
    )


async def _custom_role(ctx: Ctx, role_id: UUID) -> Role:
    role = await ctx.session.get(Role, role_id)
    if role is None or role.tenant_id != ctx.tenant_id:
        raise NotFound("custom role not found")
    return role


@router.patch("/{role_id}", response_model=RoleOut)
async def update_role(role_id: UUID, body: RoleUpdate, ctx: Ctx = Depends(require(P.USER_UPDATE))) -> RoleOut:
    role = await _custom_role(ctx, role_id)
    before = sorted(await UserRepo(ctx.session).role_permissions(role.id))
    if body.name:
        role.name = body.name
    if body.description is not None:
        role.description = body.description
    perms = before
    if body.permissions is not None:
        perms = _valid_permissions(body.permissions)
        await ctx.session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
        ctx.session.add_all(RolePermission(role_id=role.id, permission=p, tenant_id=ctx.tenant_id) for p in perms)
    await ctx.record(
        Action.PERMISSION_CHANGE, "role", role.id, before={"permissions": before}, after={"permissions": perms}
    )
    return RoleOut(
        id=role.id, key=role.key, name=role.name, description=role.description, is_system=False, permissions=perms
    )


@router.delete("/{role_id}", response_model=Ok)
async def delete_role(role_id: UUID, ctx: Ctx = Depends(require(P.USER_DELETE))) -> Ok:
    role = await _custom_role(ctx, role_id)
    in_use = (await ctx.session.execute(select(func.count()).where(Membership.role_id == role.id))).scalar_one()
    if in_use:
        raise Conflict("role is assigned to users")
    await ctx.session.delete(role)
    await ctx.record(Action.DELETE, "role", role.id)
    return Ok()
