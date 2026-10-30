from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class LimitOut(BaseModel):
    metric: str
    used: int
    limit: int
    warning: bool
    blocked: bool
    message: str | None


class BillingOut(BaseModel):
    plan_code: str
    plan_name: str
    price_cents: int
    status: str
    seats: int
    max_users: int
    trial_ends_at: datetime | None
    current_period_end: datetime | None
    onboarding_paid: bool
    limits: list[LimitOut]
    features: list[str]


class CheckoutIn(BaseModel):
    plan_code: Literal["solo", "practice"]
    include_onboarding: bool = True


class RedirectOut(BaseModel):
    url: str
