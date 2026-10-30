"""Amazon SQS queues and Step Functions workflows."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any

from complymate.adapters.aws._session import client
from complymate.ports.queue import QueueName


class SqsQueue:
    """Queue URLs are `{queue_url_prefix}{name}` — Terraform creates `complymate-{env}-{name}`."""

    def __init__(self, region: str, queue_url_prefix: str, endpoint_url: str | None = None) -> None:
        self.prefix = queue_url_prefix
        self._client = client("sqs", region, endpoint_url)

    async def send(self, queue: QueueName, message: dict[str, Any], *, delay_seconds: int = 0) -> str:
        resp = await asyncio.to_thread(
            self._client.send_message,
            QueueUrl=f"{self.prefix}{queue.value}",
            MessageBody=json.dumps(message, default=str),
            DelaySeconds=min(delay_seconds, 900),
        )
        msg_id: str = resp["MessageId"]
        return msg_id


class StepFunctionsWorkflows:
    def __init__(self, region: str, state_machines: dict[str, str | None]) -> None:
        self.state_machines = state_machines
        self._client = client("stepfunctions", region)

    async def start(self, workflow: str, payload: dict[str, Any]) -> str:
        arn = self.state_machines.get(workflow)
        if not arn:
            raise KeyError(f"no state machine configured for workflow {workflow}")
        resp = await asyncio.to_thread(
            self._client.start_execution,
            stateMachineArn=arn,
            name=f"{workflow}-{uuid.uuid4().hex[:20]}",
            input=json.dumps(payload, default=str),
        )
        execution_arn: str = resp["executionArn"]
        return execution_arn
