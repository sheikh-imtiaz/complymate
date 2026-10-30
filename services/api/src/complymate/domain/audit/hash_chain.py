"""Per-tenant hash chain over audit events. hash = SHA-256(prev_hash || canonical_json(event fields))."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

GENESIS = "0" * 64

HASHED_FIELDS = (
    "id",
    "tenant_id",
    "actor_id",
    "actor_role",
    "action",
    "resource_type",
    "resource_id",
    "before",
    "after",
    "reason",
    "ip",
    "user_agent",
    "request_id",
    "ai",
    "occurred_at",
)


def _default(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, UUID):
        return str(value)
    return str(value)


def canonical(event: Mapping[str, Any]) -> str:
    payload = {k: event.get(k) for k in HASHED_FIELDS}
    return json.dumps(payload, default=_default, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: str | None, event: Mapping[str, Any]) -> str:
    h = hashlib.sha256()
    h.update((prev_hash or GENESIS).encode())
    h.update(canonical(event).encode())
    return h.hexdigest()


@dataclass
class ChainCheck:
    ok: bool
    checked: int
    broken_at_id: str | None = None
    reason: str | None = None


def verify_chain(events: Iterable[Mapping[str, Any]], start_prev_hash: str | None = None) -> ChainCheck:
    """Events must be ordered by seq for one tenant."""
    prev = start_prev_hash or GENESIS
    count = 0
    for event in events:
        count += 1
        if (event.get("prev_hash") or GENESIS) != prev:
            return ChainCheck(False, count, str(event.get("id")), "prev_hash does not link to previous event")
        expected = compute_hash(prev, event)
        if event.get("hash") != expected:
            return ChainCheck(False, count, str(event.get("id")), "hash does not match event content")
        prev = expected
    return ChainCheck(True, count)
