from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from complymate.db.base import Base, CreatedMixin, IdMixin, TenantMixin, TimestampMixin


class Client(IdMixin, TenantMixin, TimestampMixin, Base):
    __tablename__ = "clients"

    client_type: Mapped[str] = mapped_column(String(20))
    display_name: Mapped[str] = mapped_column(String(300))
    legal_name: Mapped[str | None] = mapped_column(String(300))
    given_names: Mapped[str | None] = mapped_column(String(200))
    family_name: Mapped[str | None] = mapped_column(String(200))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    abn: Mapped[str | None] = mapped_column(String(20))
    acn: Mapped[str | None] = mapped_column(String(20))
    registration_number: Mapped[str | None] = mapped_column(String(40))
    incorporated_on: Mapped[date | None] = mapped_column(Date)
    country_of_incorporation: Mapped[str | None] = mapped_column(String(2))
    nationality: Mapped[str | None] = mapped_column(String(2))
    residential_country: Mapped[str | None] = mapped_column(String(2))
    address: Mapped[dict[str, Any]] = mapped_column(default=dict)
    occupation: Mapped[str | None] = mapped_column(String(200))
    services: Mapped[list[Any]] = mapped_column(default=list)
    channel: Mapped[str] = mapped_column(String(30), default="face_to_face")
    source_of_funds: Mapped[str | None] = mapped_column(Text)
    source_of_funds_verified: Mapped[bool] = mapped_column(default=False)
    source_of_wealth: Mapped[str | None] = mapped_column(Text)
    cash_intensive: Mapped[bool] = mapped_column(default=False)
    nominee_directors: Mapped[bool] = mapped_column(default=False)
    bearer_shares: Mapped[bool] = mapped_column(default=False)
    is_pep: Mapped[bool] = mapped_column(default=False)
    pep_details: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    risk_level: Mapped[str | None] = mapped_column(String(10))
    risk_score: Mapped[int | None]
    last_screened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_review_date: Mapped[date | None] = mapped_column(Date)
    assigned_to: Mapped[uuid.UUID | None]
    created_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_reason: Mapped[str | None] = mapped_column(Text)


class ClientParty(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "client_parties"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    parent_party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("client_parties.id", ondelete="CASCADE"))
    party_type: Mapped[str] = mapped_column(String(40))
    is_entity: Mapped[bool] = mapped_column(default=False)
    full_name: Mapped[str] = mapped_column(String(300))
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    country: Mapped[str | None] = mapped_column(String(2))
    ownership_percent: Mapped[Decimal | None] = mapped_column(Numeric(6, 3))
    has_control: Mapped[bool] = mapped_column(default=False)
    is_pep: Mapped[bool] = mapped_column(default=False)
    verified: Mapped[bool] = mapped_column(default=False)


class ClientDocument(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "client_documents"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("client_parties.id", ondelete="SET NULL"))
    doc_type: Mapped[str] = mapped_column(String(40))
    storage_key: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(String(64))
    encrypted: Mapped[bool] = mapped_column(default=True)
    ocr_status: Mapped[str] = mapped_column(String(20), default="pending")
    ocr_fields: Mapped[dict[str, Any]] = mapped_column(default=dict)
    ocr_confidence: Mapped[dict[str, Any]] = mapped_column(default=dict)
    ocr_confirmed: Mapped[bool] = mapped_column(default=False)
    confirmed_by: Mapped[uuid.UUID | None]
    uploaded_by: Mapped[uuid.UUID | None]


class Verification(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "verifications"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    party_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("client_parties.id", ondelete="SET NULL"))
    method: Mapped[str] = mapped_column(String(20), default="manual")
    checklist: Mapped[dict[str, Any]] = mapped_column(default=dict)
    result: Mapped[str] = mapped_column(String(20), default="pending")
    verified_by: Mapped[uuid.UUID | None]
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provider_ref: Mapped[str | None] = mapped_column(String(200))


class RiskAssessment(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "risk_assessments"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    rules_version: Mapped[str] = mapped_column(String(40))
    score: Mapped[int]
    level: Mapped[str] = mapped_column(String(10))
    reasons: Mapped[list[Any]] = mapped_column(default=list)
    facts: Mapped[dict[str, Any]] = mapped_column(default=dict)
    status: Mapped[str] = mapped_column(String(20), default="proposed")
    override_level: Mapped[str | None] = mapped_column(String(10))
    override_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[uuid.UUID | None]
    approved_by: Mapped[uuid.UUID | None]
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RiskFactorRow(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "risk_factors"

    assessment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("risk_assessments.id", ondelete="CASCADE"), index=True)
    factor_key: Mapped[str] = mapped_column(String(80))
    category: Mapped[str] = mapped_column(String(20))
    description: Mapped[str] = mapped_column(Text)
    points: Mapped[int]


class EddTask(IdMixin, TenantMixin, CreatedMixin, Base):
    __tablename__ = "edd_tasks"

    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    assessment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("risk_assessments.id", ondelete="SET NULL"))
    key: Mapped[str] = mapped_column(String(60))
    title: Mapped[str] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(20), default="open")
    evidence: Mapped[dict[str, Any]] = mapped_column(default=dict)
    completed_by: Mapped[uuid.UUID | None]
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_date: Mapped[date | None] = mapped_column(Date)
