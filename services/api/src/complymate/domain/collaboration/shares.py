"""Share an item with an External Advisor until an expiry date (max 90 days)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from complymate.domain.errors import ValidationFailed

SHAREABLE = {"program_version", "client", "risk_assessment", "report"}
MAX_SHARE = timedelta(days=90)


def validate(resource_type: str, expires_at: datetime, now: datetime | None = None) -> None:
    now = now or datetime.now(UTC)
    if resource_type not in SHAREABLE:
        raise ValidationFailed(f"{resource_type} cannot be shared")
    if expires_at <= now:
        raise ValidationFailed("expiry must be in the future")
    if expires_at - now > MAX_SHARE:
        raise ValidationFailed("shares can last at most 90 days")


def is_active(expires_at: datetime, revoked_at: datetime | None, now: datetime | None = None) -> bool:
    return revoked_at is None and expires_at > (now or datetime.now(UTC))
