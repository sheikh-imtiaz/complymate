from __future__ import annotations

from typing import Any


class NoopRealtime:
    """Local mode streams over FastAPI's native WebSocket, so there is nothing to push."""

    async def push(self, connection_id: str, message: dict[str, Any]) -> bool:
        return False
