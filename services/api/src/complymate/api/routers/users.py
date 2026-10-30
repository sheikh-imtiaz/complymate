from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from complymate.api.deps import Ctx, require
from complymate.db.models import User
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.users.service import assert_can_change_role, assert_can_deactivate
from complymate.schemas.common import Ok
from complymate.schemas.users import DirectoryEntry, MemberOut, RoleChangeIn

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[MemberOut])
async def list_users(ctx: Ctx = Depends(require(P.USER_READ))) -> list[dict[str, object]]:
    return await UserRepo(ctx.session).members(ctx.tenant_id)


@router.get("/directory", response_model=list[DirectoryEntry])
async def directory(ctx: Ctx = Depends(require(P.TASK_READ))) -> list[DirectoryEntry]:
    """Minimal list for assigning tasks and @mentions."""
    members = await UserRepo(ctx.session).members(ctx.tenant_id)
    return [
        DirectoryEntry(user_id=m["user_id"], full_name=m["full_name"], email=m["email"], role_key=m["role_key"])
        for m in members
        if m["status"] == "active" and m["role_key"] != "advisor"
    ]


async def _member(ctx: Ctx, user_id: UUID):  # type: ignore[no-untyped-def]
    found = await UserRepo(ctx.session).membership(ctx.tenant_id, user_id)
    if found is None:
        raise NotFound("user not found in this firm")
    return found


@router.patch("/{user_id}/role", response_model=Ok)
async def change_role(user_id: UUID, body: RoleChangeIn, ctx: Ctx = Depends(require(P.USER_UPDATE))) -> Ok:
    users = UserRepo(ctx.session)
    membership, role = await _member(ctx, user_id)
    new_role = await users.role_by_key(body.role_key, ctx.tenant_id)
    if new_role is None:
        raise NotFound("role not found")
    assert_can_change_role(ctx.principal.role_key, role.key, new_role.key, await users.owner_count(ctx.tenant_id))
    membership.role_id = new_role.id
    await ctx.record(
        Action.ROLE_CHANGE,
        "membership",
        membership.id,
        before={"role": role.key},
        after={"role": new_role.key, "user_id": str(user_id)},
        reason=body.reason,
    )
    return Ok()


@router.post("/{user_id}/deactivate", response_model=Ok)
async def deactivate(user_id: UUID, ctx: Ctx = Depends(require(P.USER_DELETE))) -> Ok:
    users = UserRepo(ctx.session)
    membership, role = await _member(ctx, user_id)
    assert_can_deactivate(role.key, await users.owner_count(ctx.tenant_id), str(ctx.user_id), str(user_id))
    membership.status = "deactivated"
    user = await ctx.session.get(User, user_id)
    if user is not None and len(await users.memberships(user_id)) == 0:
        await ctx.container.identity.sign_out_everywhere(user.external_sub)
    await ctx.record(Action.DEACTIVATE, "membership", membership.id, after={"user_id": str(user_id)})
    return Ok()


@router.post("/{user_id}/reactivate", response_model=Ok)
async def reactivate(user_id: UUID, ctx: Ctx = Depends(require(P.USER_UPDATE))) -> Ok:
    membership, _ = await _member(ctx, user_id)
    membership.status = "active"
    await ctx.record(Action.UPDATE, "membership", membership.id, after={"status": "active"})
    return Ok()


@router.post("/{user_id}/reset-mfa", response_model=Ok)
async def reset_mfa(user_id: UUID, ctx: Ctx = Depends(require(P.USER_UPDATE))) -> Ok:
    await _member(ctx, user_id)
    user = await ctx.session.get(User, user_id)
    assert user is not None
    await ctx.container.identity.reset_mfa(user.external_sub)
    user.mfa_enrolled = False
    await ctx.record(Action.PERMISSION_CHANGE, "user", user_id, after={"mfa": "reset"})
    return Ok(message="MFA reset. The user will enrol again at next sign-in.")
