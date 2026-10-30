"""Presence on the program editor: heartbeat every 20 s, viewers seen in the last 45 s are 'present'."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

HEARTBEAT_SECONDS = 20
PRESENCE_WINDOW = timedelta(seconds=45)


def cutoff(now: datetime | None = None) -> datetime:
    return (now or datetime.now(UTC)) - PRESENCE_WINDOW
