"""Authorisation policy: RBAC permission strings plus ABAC attribute rules (own, shared, tenant match, MFA).

The API layer calls `authorize` in a FastAPI dependency before the handler runs. PostgreSQL RLS checks the
tenant again at the database ("two locks, not one").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from complymate.domain.errors import Forbidden, FourEyesViolation, StepUpRequired
from complymate.domain.rbac.permissions import STEP_UP_PERMISSIONS


class Scope(StrEnum):
    ALL = "all"
    OWN = "own"
    SHARED = "shared"


@dataclass(frozen=True)
class Principal:
    user_id: UUID
    email: str
    tenant_id: UUID | None
    role_key: str | None
    permissions: frozenset[str]
    platform_role: str | None = None
    auth_time: datetime | None = None
    mfa_verified: bool = False
    impersonation_id: UUID | None = None
    api_key_id: UUID | None = None
    extra: dict[str, str] = field(default_factory=dict)

    @property
    def actor_role(self) -> str:
        if self.impersonation_id:
            return f"impersonation:{self.platform_role}"
        if self.api_key_id:
            return "api_key"
        return self.role_key or self.platform_role or "unknown"

    @property
    def is_platform(self) -> bool:
        return self.platform_role is not None and self.tenant_id is None


def scope_for(principal: Principal, permission: str) -> Scope | None:
    perms = principal.permissions
    if permission in perms:
        return Scope.ALL
    if f"{permission}:own" in perms:
        return Scope.OWN
    if f"{permission}:shared" in perms:
        return Scope.SHARED
    return None


def has_step_up(principal: Principal, window_seconds: int, now: datetime | None = None) -> bool:
    if principal.api_key_id is not None:
        return False
    if not principal.mfa_verified or principal.auth_time is None:
        return False
    now = now or datetime.now(UTC)
    return (now - principal.auth_time).total_seconds() <= window_seconds


def authorize(
    principal: Principal,
    permission: str,
    *,
    tenant_id: UUID | None = None,
    step_up_window_seconds: int = 600,
    now: datetime | None = None,
) -> Scope:
    """Returns the scope the principal holds for `permission`, or raises."""
    scope = scope_for(principal, permission)
    if scope is None:
        raise Forbidden(f"missing permission {permission}")
    if tenant_id is not None and principal.tenant_id != tenant_id:
        raise Forbidden("tenant mismatch")
    if permission in STEP_UP_PERMISSIONS and not has_step_up(principal, step_up_window_seconds, now):
        raise StepUpRequired("re-authenticate with MFA to continue")
    return scope


def check_record_access(
    scope: Scope,
    principal: Principal,
    *,
    owner_ids: set[UUID | None] | None = None,
    shared_with: set[UUID] | None = None,
) -> None:
    """ABAC: `own` means the principal created or is assigned to the record; `shared` means an active share."""
    if scope is Scope.ALL:
        return
    if scope is Scope.OWN and principal.user_id in (owner_ids or set()):
        return
    if scope is Scope.SHARED and principal.user_id in (shared_with or set()):
        return
    raise Forbidden("record not accessible")


def assert_four_eyes(created_by: UUID | None, approver: UUID) -> None:
    """The person who creates a high-risk decision cannot approve it."""
    if created_by is not None and created_by == approver:
        raise FourEyesViolation("a second person must approve this decision")
