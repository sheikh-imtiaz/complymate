from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin


class User(IdMixin, CreatedMixin, Base):
    __tablename__ = "users"

    external_sub: Mapped[str] = mapped_column(String(200), unique=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    full_name: Mapped[str | None] = mapped_column(String(200))
    platform_role: Mapped[str | None] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(20), default="active")
    mfa_enrolled: Mapped[bool] = mapped_column(default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Role(IdMixin, CreatedMixin, Base):
    __tablename__ = "roles"

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(60))
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(default=False)
    base_role_key: Mapped[str | None] = mapped_column(String(60))


class RolePermission(Base):
    __tablename__ = "role_permissions"

    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission: Mapped[str] = mapped_column(String(80), primary_key=True)
    tenant_id: Mapped[uuid.UUID | None]


class Membership(IdMixin, CreatedMixin, Base):
    __tablename__ = "memberships"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    status: Mapped[str] = mapped_column(String(20), default="active")
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Invitation(IdMixin, CreatedMixin, Base):
    __tablename__ = "invitations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    email: Mapped[str] = mapped_column(String(320))
    full_name: Mapped[str | None] = mapped_column(String(200))
    role_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("roles.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    invited_by: Mapped[uuid.UUID | None]
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApiKey(IdMixin, CreatedMixin, Base):
    __tablename__ = "api_keys"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    prefix: Mapped[str] = mapped_column(String(16), unique=True)
    key_hash: Mapped[str] = mapped_column(String(64))
    permissions: Mapped[list[Any]] = mapped_column(default=list)
    created_by: Mapped[uuid.UUID | None]
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
