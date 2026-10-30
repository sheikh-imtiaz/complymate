from __future__ import annotations

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Membership, Role, RolePermission, Tenant, User


class UserRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def get(self, user_id: UUID) -> User | None:
        return await self.s.get(User, user_id)

    async def by_sub(self, sub: str) -> User | None:
        return (await self.s.execute(select(User).where(User.external_sub == sub))).scalar_one_or_none()

    async def by_email(self, email: str) -> User | None:
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return (await self.s.execute(stmt)).scalar_one_or_none()

    async def get_or_create(self, sub: str, email: str, full_name: str | None) -> User:
        user = await self.by_sub(sub)
        if user is None:
            user = await self.by_email(email)
            if user is not None:
                user.external_sub = sub  # invited user signing in for the first time
            else:
                user = User(external_sub=sub, email=email.lower(), full_name=full_name)
                self.s.add(user)
            await self.s.flush()
        return user

    async def memberships(self, user_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(Membership, Tenant.name, Tenant.status, Role.key, Role.name)
            .join(Tenant, Tenant.id == Membership.tenant_id)
            .join(Role, Role.id == Membership.role_id)
            .where(Membership.user_id == user_id, Membership.status == "active")
        )
        out = []
        for m, tname, tstatus, rkey, rname in (await self.s.execute(stmt)).all():
            out.append(
                {
                    "tenant_id": m.tenant_id,
                    "tenant_name": tname,
                    "tenant_status": tstatus,
                    "role_key": rkey,
                    "role_name": rname,
                    "expires_at": m.expires_at,
                }
            )
        return out

    async def membership(self, tenant_id: UUID, user_id: UUID) -> tuple[Membership, Role] | None:
        stmt = (
            select(Membership, Role)
            .join(Role, Role.id == Membership.role_id)
            .where(Membership.tenant_id == tenant_id, Membership.user_id == user_id)
        )
        row = (await self.s.execute(stmt)).first()
        return (row[0], row[1]) if row else None

    async def role_permissions(self, role_id: UUID) -> frozenset[str]:
        rows = await self.s.execute(select(RolePermission.permission).where(RolePermission.role_id == role_id))
        return frozenset(r for (r,) in rows.all())

    async def role_by_key(self, key: str, tenant_id: UUID | None = None) -> Role | None:
        stmt = select(Role).where(Role.key == key)
        stmt = (
            stmt.where((Role.tenant_id == tenant_id) | Role.tenant_id.is_(None))
            if tenant_id
            else stmt.where(Role.tenant_id.is_(None))
        )
        rows = (await self.s.execute(stmt)).scalars().all()
        # Tenant custom role wins over a system role with the same key.
        return sorted(rows, key=lambda r: r.tenant_id is None)[0] if rows else None

    async def roles(self, tenant_id: UUID) -> Sequence[Role]:
        stmt = (
            select(Role)
            .where((Role.tenant_id == tenant_id) | Role.tenant_id.is_(None))
            .order_by(Role.is_system.desc(), Role.name)
        )
        return (await self.s.execute(stmt)).scalars().all()

    async def members(self, tenant_id: UUID) -> list[dict[str, Any]]:
        stmt = (
            select(User, Membership, Role)
            .join(Membership, Membership.user_id == User.id)
            .join(Role, Role.id == Membership.role_id)
            .where(Membership.tenant_id == tenant_id)
            .order_by(User.full_name)
        )
        return [
            {
                "user_id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "status": m.status,
                "role_key": r.key,
                "role_name": r.name,
                "role_id": r.id,
                "mfa_enrolled": u.mfa_enrolled,
                "last_login_at": u.last_login_at,
                "membership_id": m.id,
                "expires_at": m.expires_at,
            }
            for u, m, r in (await self.s.execute(stmt)).all()
        ]

    async def users_with_role(self, tenant_id: UUID, role_keys: tuple[str, ...]) -> list[User]:
        stmt = (
            select(User)
            .join(Membership, Membership.user_id == User.id)
            .join(Role, Role.id == Membership.role_id)
            .where(Membership.tenant_id == tenant_id, Membership.status == "active", Role.key.in_(role_keys))
        )
        return list((await self.s.execute(stmt)).scalars().all())

    async def owner_count(self, tenant_id: UUID) -> int:
        return len(await self.users_with_role(tenant_id, ("owner",)))
