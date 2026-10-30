"""Invitation tokens: random, single use, stored as SHA-256 hash, 7 day expiry."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

INVITE_TTL = timedelta(days=7)


def new_token() -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    return token, hash_token(token)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def expiry(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) + INVITE_TTL


def is_usable(
    expires_at: datetime, accepted_at: datetime | None, revoked_at: datetime | None, now: datetime | None = None
) -> bool:
    now = now or datetime.now(UTC)
    return accepted_at is None and revoked_at is None and expires_at > now
