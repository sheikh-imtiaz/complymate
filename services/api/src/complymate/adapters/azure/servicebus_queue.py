"""Azure Service Bus queues and Durable Functions-style workflow starter."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from complymate.adapters.azure._credential import async_credential
from complymate.ports.queue import QueueName


class ServiceBusQueue:
    def __init__(self, namespace: str, queue_prefix: str = "") -> None:
        from azure.servicebus.aio import ServiceBusClient

        self.prefix = queue_prefix
        self._client = ServiceBusClient(f"{namespace}.servicebus.windows.net", credential=async_credential())

    async def send(self, queue: QueueName, message: dict[str, Any], *, delay_seconds: int = 0) -> str:
        from azure.servicebus import ServiceBusMessage

        msg_id = str(uuid.uuid4())
        msg = ServiceBusMessage(json.dumps(message, default=str), message_id=msg_id, content_type="application/json")
        if delay_seconds:
            msg.scheduled_enqueue_time_utc = datetime.now(UTC) + timedelta(seconds=delay_seconds)
        async with self._client.get_queue_sender(f"{self.prefix}{queue.value}") as sender:
            await sender.send_messages(msg)
        return msg_id


class DurableWorkflows:
    """Starts a Durable Functions orchestration over HTTP (function key in Key Vault)."""

    def __init__(self, base_url: str, function_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.function_key = function_key

    async def start(self, workflow: str, payload: dict[str, Any]) -> str:
        async with httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{self.base_url}/api/orchestrators/{workflow}",
                params={"code": self.function_key},
                json=payload,
            )
            resp.raise_for_status()
            return str(resp.json()["id"])
