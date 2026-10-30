from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from complymate.schemas.common import ORM

ClientType = Literal["individual", "company", "trust", "partnership"]
Channel = Literal["face_to_face", "non_face_to_face", "intermediary"]


def _country(v: str | None) -> str | None:
    if v is None or v == "":
        return None
    if len(v) != 2 or not v.isalpha():
        raise ValueError("use a 2-letter ISO country code")
    return v.upper()


class ClientBase(BaseModel):
    legal_name: str | None = Field(default=None, max_length=300)
    given_names: str | None = Field(default=None, max_length=200)
    family_name: str | None = Field(default=None, max_length=200)
    date_of_birth: date | None = None
    abn: str | None = None
    acn: str | None = None
    registration_number: str | None = None
    incorporated_on: date | None = None
    country_of_incorporation: str | None = None
    nationality: str | None = None
    residential_country: str | None = None
    address: dict[str, Any] = {}
    occupation: str | None = None
    services: list[str] = []
    channel: Channel = "face_to_face"
    source_of_funds: str | None = None
    source_of_funds_verified: bool = False
    source_of_wealth: str | None = None
    cash_intensive: bool = False
    nominee_directors: bool = False
    bearer_shares: bool = False
    is_pep: bool = False
    pep_details: str | None = None
    assigned_to: UUID | None = None

    @field_validator("country_of_incorporation", "nationality", "residential_country")
    @classmethod
    def _countries(cls, v: str | None) -> str | None:
        return _country(v)


class ClientCreate(ClientBase):
    client_type: ClientType


class ClientUpdate(BaseModel):
    legal_name: str | None = None
    given_names: str | None = None
    family_name: str | None = None
    date_of_birth: date | None = None
    abn: str | None = None
    acn: str | None = None
    registration_number: str | None = None
    incorporated_on: date | None = None
    country_of_incorporation: str | None = None
    nationality: str | None = None
    residential_country: str | None = None
    address: dict[str, Any] | None = None
    occupation: str | None = None
    services: list[str] | None = None
    channel: Channel | None = None
    source_of_funds: str | None = None
    source_of_funds_verified: bool | None = None
    source_of_wealth: str | None = None
    cash_intensive: bool | None = None
    nominee_directors: bool | None = None
    bearer_shares: bool | None = None
    is_pep: bool | None = None
    pep_details: str | None = None
    assigned_to: UUID | None = None

    @field_validator("country_of_incorporation", "nationality", "residential_country")
    @classmethod
    def _countries(cls, v: str | None) -> str | None:
        return _country(v)


class ClientOut(ORM):
    id: UUID
    client_type: str
    display_name: str
    legal_name: str | None
    given_names: str | None
    family_name: str | None
    date_of_birth: date | None
    abn: str | None
    acn: str | None
    registration_number: str | None
    incorporated_on: date | None
    country_of_incorporation: str | None
    nationality: str | None
    residential_country: str | None
    address: dict[str, Any]
    occupation: str | None
    services: list[str]
    channel: str
    source_of_funds: str | None
    source_of_funds_verified: bool
    source_of_wealth: str | None
    cash_intensive: bool
    nominee_directors: bool
    bearer_shares: bool
    is_pep: bool
    pep_details: str | None
    status: str
    risk_level: str | None
    risk_score: int | None
    last_screened_at: datetime | None
    next_review_date: date | None
    assigned_to: UUID | None
    created_by: UUID | None
    approved_by: UUID | None
    approved_at: datetime | None
    status_reason: str | None
    created_at: datetime
    updated_at: datetime


class ClientListItem(ORM):
    id: UUID
    client_type: str
    display_name: str
    status: str
    risk_level: str | None
    next_review_date: date | None
    assigned_to: UUID | None
    updated_at: datetime


class PartyIn(BaseModel):
    parent_party_id: UUID | None = None
    party_type: Literal[
        "beneficial_owner",
        "director",
        "trustee",
        "settlor",
        "beneficiary",
        "partner",
        "shareholder_entity",
        "appointor",
        "protector",
    ]
    is_entity: bool = False
    full_name: str = Field(min_length=1, max_length=300)
    date_of_birth: date | None = None
    country: str | None = None
    ownership_percent: Decimal | None = Field(default=None, ge=0, le=100)
    has_control: bool = False
    is_pep: bool = False
    verified: bool = False

    @field_validator("country")
    @classmethod
    def _country_code(cls, v: str | None) -> str | None:
        return _country(v)


class PartyOut(ORM):
    id: UUID
    parent_party_id: UUID | None
    party_type: str
    is_entity: bool
    full_name: str
    date_of_birth: date | None
    country: str | None
    ownership_percent: Decimal | None
    has_control: bool
    is_pep: bool
    verified: bool


class StatusChangeIn(BaseModel):
    reason: str = Field(min_length=3, max_length=2000)


class VerificationIn(BaseModel):
    party_id: UUID | None = None
    method: Literal["manual", "electronic"] = "manual"
    checklist: dict[str, bool]
    result: Literal["pending", "passed", "failed"]


class VerificationOut(ORM):
    id: UUID
    party_id: UUID | None
    method: str
    checklist: dict[str, Any]
    result: str
    verified_by: UUID | None
    verified_at: datetime | None
    created_at: datetime


class CddChecklistOut(BaseModel):
    client_type: str
    required_fields: list[str]
    missing_fields: list[str]
    verify_with_one_of: list[list[str]]
    documents_present: list[str]
    checklist: list[str]
    verifications: list[VerificationOut]
