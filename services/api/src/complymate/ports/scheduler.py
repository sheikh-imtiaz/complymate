from __future__ import annotations

from typing import Any, Protocol


class Scheduler(Protocol):
    """Cron schedules that enqueue a worker task (EventBridge Scheduler / Container Apps Jobs / local cron)."""

    async def upsert_schedule(self, name: str, cron: str, task: str, payload: dict[str, Any]) -> None: ...

    async def delete_schedule(self, name: str) -> None: ...
