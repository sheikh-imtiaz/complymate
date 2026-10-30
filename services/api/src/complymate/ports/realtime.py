from __future__ import annotations

from typing import Any, Protocol


class RealtimePusher(Protocol):
    """Pushes messages to a connected WebSocket client (API Gateway WebSocket on AWS)."""

    async def push(self, connection_id: str, message: dict[str, Any]) -> bool: ...
