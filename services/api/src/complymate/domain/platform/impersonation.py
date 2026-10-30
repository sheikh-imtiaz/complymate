"""Support impersonation: needs tenant consent, a reason and a time limit (max 60 minutes)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from complymate.domain.errors import Forbidden, ValidationFailed

MAX_DURATION = timedelta(minutes=60)


def validate_request(reason: str, minutes: int) -> timedelta:
    if len((reason or "").strip()) < 10:
        raise ValidationFailed("give a reason of at least 10 characters")
    duration = timedelta(minutes=minutes)
    if duration <= timedelta(0) or duration > MAX_DURATION:
        raise ValidationFailed("impersonation lasts between 1 and 60 minutes")
    return duration


def assert_active(
    consented_at: datetime | None, expires_at: datetime | None, ended_at: datetime | None, now: datetime | None = None
) -> None:
    now = now or datetime.now(UTC)
    if consented_at is None:
        raise Forbidden("tenant has not consented to this support session")
    if ended_at is not None or expires_at is None or expires_at <= now:
        raise Forbidden("support session has expired")
