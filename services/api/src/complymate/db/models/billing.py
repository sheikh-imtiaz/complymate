from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin


class PlanRow(Base):
    __tablename__ = "plans"

    code: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    price_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(String(3), default="aud")
    max_users: Mapped[int]
    limits: Mapped[dict[str, Any]] = mapped_column(default=dict)
    stripe_price_id: Mapped[str | None] = mapped_column(String(100))


class Subscription(IdMixin, TenantMixin, Base):
    __tablename__ = "subscriptions"

    plan_code: Mapped[str] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(20), default="trialing")
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100))
    seats: Mapped[int] = mapped_column(default=1)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    onboarding_paid: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UsageCounter(Base):
    __tablename__ = "usage_counters"

    tenant_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    period: Mapped[str] = mapped_column(String(7), primary_key=True)
    metric: Mapped[str] = mapped_column(String(40), primary_key=True)
    value: Mapped[int] = mapped_column(BigInteger, default=0)


class FeatureFlag(IdMixin, Base):
    __tablename__ = "feature_flags"

    key: Mapped[str] = mapped_column(String(60))
    tenant_id: Mapped[uuid.UUID | None]
    enabled: Mapped[bool] = mapped_column(default=False)
    updated_by: Mapped[uuid.UUID | None]
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ImpersonationSession(IdMixin, CreatedMixin, Base):
    __tablename__ = "impersonation_sessions"

    tenant_id: Mapped[uuid.UUID] = mapped_column(index=True)
    support_user_id: Mapped[uuid.UUID]
    reason: Mapped[str] = mapped_column(Text)
    duration_minutes: Mapped[int]
    consented_by: Mapped[uuid.UUID | None]
    consented_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ReportJob(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "report_jobs"

    report_type: Mapped[str] = mapped_column(String(40))
    params: Mapped[dict[str, Any]] = mapped_column(default=dict)
    format: Mapped[str] = mapped_column(String(10), default="csv")
    status: Mapped[str] = mapped_column(String(20), default="queued")
    requested_by: Mapped[uuid.UUID | None]
    schedule_cron: Mapped[str | None] = mapped_column(String(60))
    recipients: Mapped[list[Any]] = mapped_column(default=list)
    export_id: Mapped[uuid.UUID | None]
    error: Mapped[str | None] = mapped_column(Text)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Export(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "exports"

    kind: Mapped[str] = mapped_column(String(40))
    storage_key: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    created_by: Mapped[uuid.UUID | None]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StripeEvent(Base):
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(100), primary_key=True)
    type: Mapped[str] = mapped_column(String(100))
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    payload_summary: Mapped[str | None] = mapped_column(Text)
