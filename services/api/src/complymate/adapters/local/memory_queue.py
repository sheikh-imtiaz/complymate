"""In-process queue. Messages run as background asyncio tasks (dev) or are collected (tests)."""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Callable, Coroutine
from typing import Any

import structlog

from complymate.ports.queue import QueueName

log = structlog.get_logger(__name__)
Dispatcher = Callable[[str, dict[str, Any]], Coroutine[Any, Any, Any]]


class MemoryQueue:
    def __init__(self, dispatcher: Dispatcher | None = None, run_inline: bool = True) -> None:
        self.dispatcher = dispatcher
        self.run_inline = run_inline
        self.sent: list[tuple[QueueName, dict[str, Any]]] = []
        self._tasks: set[asyncio.Task[Any]] = set()

    async def send(self, queue: QueueName, message: dict[str, Any], *, delay_seconds: int = 0) -> str:
        msg_id = str(uuid.uuid4())
        self.sent.append((queue, message))
        if self.run_inline and self.dispatcher is not None:
            task = asyncio.create_task(self._run(message, delay_seconds))
            self._tasks.add(task)
            task.add_done_callback(self._tasks.discard)
        return msg_id

    async def _run(self, message: dict[str, Any], delay: int) -> None:
        if delay:
            await asyncio.sleep(delay)
        try:
            assert self.dispatcher is not None
            await self.dispatcher(message["task"], message.get("payload", {}))
        except Exception:  # pragma: no cover - logged for dev visibility
            log.exception("memory_queue.task_failed", task=message.get("task"))

    async def drain(self) -> None:
        while self._tasks:
            await asyncio.gather(*list(self._tasks), return_exceptions=True)


class InProcessWorkflows:
    """Runs workflow steps sequentially in-process (local stand-in for Step Functions)."""

    def __init__(self, dispatcher: Dispatcher | None = None) -> None:
        self.dispatcher = dispatcher

    async def start(self, workflow: str, payload: dict[str, Any]) -> str:
        if self.dispatcher is not None:
            task = asyncio.create_task(self.dispatcher(f"workflow:{workflow}", payload))
            task.add_done_callback(lambda _t: None)
        return f"local-{workflow}-{uuid.uuid4()}"
