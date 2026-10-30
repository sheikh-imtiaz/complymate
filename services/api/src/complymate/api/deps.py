"""Request context: authenticates the caller, resolves the tenant, opens ONE transaction with RLS context and
exposes `require(permission)` — the dependency every route uses to declare the permission it needs."""

from __future__ import annotations

import ipaddress
from collections.abc import AsyncIterator, Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import jwt
import structlog
from fastapi import Depends, Request
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.api.errors import Unauthorized
from complymate.api.middleware.audit import client_ip_var, user_agent_var
from complymate.container import Container, get_container
from complymate.db.models import ImpersonationSession, Tenant, TenantSettings, User
from complymate.db.repositories.audit import AuditRepo
from complymate.db.repositories.billing import BillingRepo
from complymate.db.repositories.tasks import TaskRepo
from complymate.db.repositories.users import UserRepo
from complymate.db.session import apply_context
from complymate.domain.api_keys.service import hash_key, parse_prefix
from complymate.domain.audit.events import Action, AuditContext
from complymate.domain.audit.service import AuditService
from complymate.domain.errors import Forbidden
from complymate.domain.platform.impersonation import assert_active
from complymate.domain.rbac.policy import Principal, Scope, authorize
from complymate.domain.rbac.roles import AMLCO, OWNER, PLATFORM_ROLES, SUPPORT_IMPERSONATION
from complymate.observability import metrics
from complymate.observability.logging import request_id_var, tenant_id_var, user_id_var

log = structlog.get_logger("security")


@dataclass
class Ctx:
    principal: Principal
    session: AsyncSession
    container: Container
    request_id: str | None
    ip: str | None
    user_agent: str | None
    scope: Scope = Scope.ALL
    user: User | None = None
    _audit: AuditService | None = field(default=None, repr=False)

    @property
    def tenant_id(self) -> UUID:
        if self.principal.tenant_id is None:
            raise Forbidden("select a firm first")
        return self.principal.tenant_id

    @property
    def user_id(self) -> UUID:
        return self.principal.user_id

    @property
    def audit_ctx(self) -> AuditContext:
        return AuditContext(
            actor_id=self.principal.user_id,
            actor_role=self.principal.actor_role,
            tenant_id=self.principal.tenant_id,
            ip=self.ip,
            user_agent=self.user_agent,
            request_id=self.request_id,
        )

    @property
    def audit(self) -> AuditService:
        if self._audit is None:
            self._audit = AuditService(AuditRepo(self.session))
        return self._audit

    async def record(self, action: str, resource_type: str, resource_id: Any, **kwargs: Any) -> None:
        await self.audit.record(self.audit_ctx, action, resource_type, resource_id, **kwargs)

    @property
    def tasks(self) -> TaskRepo:
        return TaskRepo(self.session)

    @property
    def billing(self) -> BillingRepo:
        return BillingRepo(self.session)


def _bearer(request: Request) -> str | None:
    header = request.headers.get("authorization", "")
    if header.lower().startswith("bearer "):
        return header[7:].strip()
    return request.query_params.get("access_token") if request.url.path.startswith("/ws") else None


def _uuid_header(request: Request, name: str) -> UUID | None:
    raw = request.headers.get(name)
    if not raw:
        return None
    try:
        return UUID(raw)
    except ValueError as exc:
        raise Unauthorized(f"invalid {name} header") from exc


def _ip_allowed(ip: str | None, allow_list: list[str]) -> bool:
    if not allow_list:
        return True
    if not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in ipaddress.ip_network(net, strict=False) for net in allow_list)


async def _api_key_principal(session: AsyncSession, key: str) -> Principal:
    prefix = parse_prefix(key)
    if not prefix:
        raise Unauthorized("invalid API key")
    row = (await session.execute(text("SELECT * FROM app_api_key_lookup(:p)"), {"p": prefix})).mappings().first()
    now = datetime.now(UTC)
    if (
        row is None
        or row["key_hash"] != hash_key(key)
        or row["revoked_at"] is not None
        or (row["expires_at"] is not None and row["expires_at"] <= now)
    ):
        log.warning("security_event", category="api_key_rejected")
        metrics.security_event("api_key_rejected")
        raise Unauthorized("invalid API key")
    await apply_context(session, row["tenant_id"])
    await session.execute(text("UPDATE api_keys SET last_used_at = now() WHERE id = :id"), {"id": row["id"]})
    return Principal(
        user_id=row["created_by"],
        email="api-key",
        tenant_id=row["tenant_id"],
        role_key=None,
        permissions=frozenset(row["permissions"]),
        api_key_id=row["id"],
    )


async def authenticate(request: Request, session: AsyncSession, container: Container) -> tuple[Principal, User | None]:
    if api_key := request.headers.get("x-api-key"):
        return await _api_key_principal(session, api_key), None

    token = _bearer(request)
    if not token:
        raise Unauthorized("missing bearer token")
    try:
        claims = await container.identity.verify_token(token)
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        log.warning("security_event", category="login_failed", reason=type(exc).__name__)
        metrics.security_event("login_failed")
        raise Unauthorized("invalid or expired token") from exc

    users = UserRepo(session)
    user = await users.get_or_create(claims.sub, claims.email, claims.name)
    if user.status != "active":
        raise Unauthorized("account is deactivated")
    await apply_context(session, None, user_id=user.id)

    requested_tenant = _uuid_header(request, "x-tenant-id")
    impersonation_id = _uuid_header(request, "x-impersonation-id")
    base: dict[str, Any] = dict(
        user_id=user.id, email=user.email, auth_time=claims.auth_time, mfa_verified=claims.mfa_verified
    )

    # Platform staff: impersonation (with consent) / break-glass / platform scope.
    if user.platform_role:
        if impersonation_id:
            await apply_context(session, None, platform=True, user_id=user.id)
            imp = await session.get(ImpersonationSession, impersonation_id)
            if imp is None or imp.support_user_id != user.id:
                raise Forbidden("unknown support session")
            assert_active(imp.consented_at, imp.expires_at, imp.ended_at)
            return Principal(
                **base,
                tenant_id=imp.tenant_id,
                role_key=SUPPORT_IMPERSONATION.key,
                permissions=SUPPORT_IMPERSONATION.permissions,
                platform_role=user.platform_role,
                impersonation_id=imp.id,
            ), user
        reason = request.headers.get("x-break-glass-reason")
        if requested_tenant and user.platform_role == "super_admin" and reason:
            return Principal(
                **base,
                tenant_id=requested_tenant,
                role_key="break_glass",
                permissions=OWNER.permissions | AMLCO.permissions,
                platform_role=user.platform_role,
                extra={"break_glass_reason": reason[:300]},
            ), user
        if not requested_tenant:
            return Principal(
                **base,
                tenant_id=None,
                role_key=None,
                permissions=PLATFORM_ROLES[user.platform_role],
                platform_role=user.platform_role,
            ), user

    memberships = await users.memberships(user.id)
    if requested_tenant is None:
        if len(memberships) != 1:
            # No tenant chosen: authenticated but tenant-less (sign-up, tenant switcher, /auth/me).
            return Principal(**base, tenant_id=None, role_key=None, permissions=frozenset()), user
        requested_tenant = memberships[0]["tenant_id"]

    found = await users.membership(requested_tenant, user.id)
    if found is None or found[0].status != "active":
        raise Forbidden("you are not a member of this firm")
    membership, role = found
    if membership.expires_at and membership.expires_at <= datetime.now(UTC):
        raise Forbidden("your access to this firm has expired")
    perms = await users.role_permissions(role.id)
    return Principal(
        **base, tenant_id=requested_tenant, role_key=role.base_role_key or role.key, permissions=perms
    ), user


async def get_ctx(request: Request) -> AsyncIterator[Ctx]:
    container = get_container()
    maker = await container.sessionmaker()
    async with maker() as session, session.begin():
        principal, user = await authenticate(request, session, container)
        await apply_context(session, principal.tenant_id, platform=principal.is_platform, user_id=principal.user_id)
        ctx = Ctx(
            principal=principal,
            session=session,
            container=container,
            request_id=request_id_var.get(),
            ip=client_ip_var.get(),
            user_agent=user_agent_var.get(),
            user=user,
        )
        user_id_var.set(str(principal.user_id))
        if principal.tenant_id:
            tenant_id_var.set(str(principal.tenant_id))
            await _tenant_guards(ctx)
        yield ctx


async def _tenant_guards(ctx: Ctx) -> None:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    if tenant is None:
        raise Forbidden("firm not found")
    if tenant.status == "suspended" and not ctx.principal.platform_role:
        raise Forbidden("this firm's account is suspended; contact support")
    settings = (
        await ctx.session.execute(select(TenantSettings).where(TenantSettings.tenant_id == ctx.tenant_id))
    ).scalar_one_or_none()
    if settings is not None and not ctx.principal.platform_role:
        if not _ip_allowed(ctx.ip, list(settings.ip_allow_list or [])):
            await ctx.record(Action.LOGIN_FAILED, "tenant", ctx.tenant_id, reason="ip_not_allowed")
            raise Forbidden("access from this network is not allowed for this firm")
        if settings.mfa_required and not ctx.principal.mfa_verified and ctx.principal.api_key_id is None:
            raise Forbidden("this firm requires multi-factor authentication")
    if ctx.principal.extra.get("break_glass_reason"):
        await ctx.record(Action.BREAK_GLASS, "tenant", ctx.tenant_id, reason=ctx.principal.extra["break_glass_reason"])
    if ctx.principal.api_key_id:
        await ctx.record(Action.API_KEY_USE, "api_key", ctx.principal.api_key_id)


def require(permission: str) -> Callable[..., Coroutine[Any, Any, Ctx]]:
    """Route dependency: `ctx: Ctx = Depends(require(P.CLIENT_READ))`."""

    async def dependency(ctx: Ctx = Depends(get_ctx)) -> Ctx:
        ctx.scope = authorize(
            ctx.principal, str(permission), step_up_window_seconds=ctx.container.settings.step_up_mfa_seconds
        )
        return ctx

    dependency.__name__ = f"require_{str(permission).replace(':', '_')}"
    return dependency


async def authenticated(ctx: Ctx = Depends(get_ctx)) -> Ctx:
    """Any signed-in user, with or without a tenant."""
    return ctx


async def require_platform(ctx: Ctx = Depends(get_ctx)) -> Ctx:
    if not ctx.principal.is_platform:
        raise Forbidden("platform staff only")
    return ctx
