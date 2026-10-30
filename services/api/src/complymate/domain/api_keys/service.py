"""API keys: `cm_<prefix>_<secret>`. Only the SHA-256 hash is stored. Permissions are a subset of the creator's."""

from __future__ import annotations

import hashlib
import secrets

from complymate.domain.errors import Forbidden

PREFIX = "cm"


def generate() -> tuple[str, str, str]:
    """Returns (full_key, prefix, key_hash). Show full_key once."""
    prefix = secrets.token_hex(4)
    secret = secrets.token_urlsafe(32)
    full = f"{PREFIX}_{prefix}_{secret}"
    return full, prefix, hash_key(full)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def parse_prefix(key: str) -> str | None:
    parts = key.split("_", 2)
    if len(parts) != 3 or parts[0] != PREFIX:
        return None
    return parts[1]


def assert_subset(requested: set[str], creator_permissions: frozenset[str]) -> None:
    extra = requested - set(creator_permissions)
    if extra:
        raise Forbidden(f"cannot grant permissions you do not hold: {sorted(extra)}")
    # API keys never get approval, SMR or user-management powers.
    blocked = {p for p in requested if p.endswith(":approve") or p.startswith(("smr:", "user:", "billing:"))}
    if blocked:
        raise Forbidden(f"permissions not allowed for API keys: {sorted(blocked)}")
