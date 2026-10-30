from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from complymate.schemas.common import ORM


class ServiceQuestionOut(BaseModel):
    code: str
    question: str
    designated: bool
    sector: str


class ApplicabilityIn(BaseModel):
    jurisdiction: Literal["AU", "NZ"] = "AU"
    services: list[str] = []


class ApplicabilityOut(BaseModel):
    applies: bool
    jurisdiction: str
    designated_services: list[str]
    explanation: str


class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    jurisdiction: Literal["AU", "NZ"] = "AU"
    entity_type: str | None = Field(default=None, max_length=40)
    abn: str | None = Field(default=None, max_length=20)
    nzbn: str | None = Field(default=None, max_length=20)
    services: list[str] = []
    size: str | None = None
    plan_code: Literal["solo", "practice"] = "solo"

    @field_validator("abn")
    @classmethod
    def abn_digits(cls, v: str | None) -> str | None:
        if v is None:
            return v
        digits = "".join(ch for ch in v if ch.isdigit())
        if len(digits) != 11:
            raise ValueError("ABN must have 11 digits")
        weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
        nums = [int(d) for d in digits]
        nums[0] -= 1
        if sum(w * n for w, n in zip(weights, nums, strict=True)) % 89 != 0:
            raise ValueError("ABN checksum is invalid")
        return digits


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=200)
    entity_type: str | None = None
    abn: str | None = None
    nzbn: str | None = None
    services: list[str] | None = None
    size: str | None = None


class TenantOut(ORM):
    id: UUID
    name: str
    slug: str
    jurisdiction: str
    entity_type: str | None
    abn: str | None
    nzbn: str | None
    services: list[str]
    size: str | None
    status: str
    tranche2_applies: bool | None
    amlco_user_id: UUID | None
    plan_code: str
    created_at: datetime


class AmlcoIn(BaseModel):
    user_id: UUID


class SettingsOut(ORM):
    mfa_required: bool
    session_timeout_minutes: int
    ip_allow_list: list[str]
    retention_years: int
    branding: dict[str, Any]
    integrations: dict[str, Any]
    onboarding: dict[str, Any]
    allow_support_impersonation: bool


class SettingsUpdate(BaseModel):
    mfa_required: bool | None = None
    session_timeout_minutes: int | None = Field(default=None, ge=5, le=720)
    ip_allow_list: list[str] | None = None
    retention_years: int | None = Field(default=None, ge=7, le=50)
    branding: dict[str, Any] | None = None
    integrations: dict[str, Any] | None = None
    onboarding: dict[str, Any] | None = None
    allow_support_impersonation: bool | None = None


class ImpersonationConsentIn(BaseModel):
    approve: bool
