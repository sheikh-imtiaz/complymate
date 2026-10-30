from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, LargeBinary, String, func
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, IdMixin, TimestampMixin


class Tenant(IdMixin, TimestampMixin, Base):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    jurisdiction: Mapped[str] = mapped_column(String(2), default="AU")
    entity_type: Mapped[str | None] = mapped_column(String(40))
    abn: Mapped[str | None] = mapped_column(String(20))
    nzbn: Mapped[str | None] = mapped_column(String(20))
    services: Mapped[list[Any]] = mapped_column(default=list)
    size: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="trial")
    tranche2_applies: Mapped[bool | None]
    amlco_user_id: Mapped[uuid.UUID | None]
    plan_code: Mapped[str] = mapped_column(String(20), default="solo")


class TenantSettings(Base):
    __tablename__ = "tenant_settings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    mfa_required: Mapped[bool] = mapped_column(default=True)
    session_timeout_minutes: Mapped[int] = mapped_column(default=30)
    ip_allow_list: Mapped[list[Any]] = mapped_column(default=list)
    retention_years: Mapped[int] = mapped_column(default=7)
    branding: Mapped[dict[str, Any]] = mapped_column(default=dict)
    integrations: Mapped[dict[str, Any]] = mapped_column(default=dict)
    onboarding: Mapped[dict[str, Any]] = mapped_column(default=dict)
    allow_support_impersonation: Mapped[bool] = mapped_column(default=False)
    encrypted_data_key: Mapped[bytes | None] = mapped_column(LargeBinary)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
