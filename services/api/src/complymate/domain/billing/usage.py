"""Usage metering: agent turns, documents, users. Counted per calendar month (UTC)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum


class Metric(StrEnum):
    AGENT_TURNS = "agent_turns"
    DOCUMENTS = "documents"
    USERS = "users"
    CLIENTS = "clients"


def period(now: datetime | None = None) -> str:
    return (now or datetime.now(UTC)).strftime("%Y-%m")
