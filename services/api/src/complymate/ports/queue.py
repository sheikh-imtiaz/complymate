from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol


class QueueName(StrEnum):
    OCR = "ocr"
    SCREENING = "screening"
    EXPORTS = "exports"
    NOTIFICATIONS = "notifications"
    AUDIT = "audit"


class Queue(Protocol):
    async def send(self, queue: QueueName, message: dict[str, Any], *, delay_seconds: int = 0) -> str: ...


class WorkflowStarter(Protocol):
    """Starts multi-step workflows (Step Functions / Durable Functions / in-process locally)."""

    async def start(self, workflow: str, payload: dict[str, Any]) -> str: ...
