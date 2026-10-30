"""EventBridge Scheduler: each schedule sends `{"task": ..., "payload": ...}` to the worker SQS queue."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from complymate.adapters.aws._session import client


class EventBridgeScheduler:
    def __init__(self, region: str, group: str, role_arn: str, target_queue_arn: str) -> None:
        self.group = group
        self.role_arn = role_arn
        self.target_queue_arn = target_queue_arn
        self._client = client("scheduler", region)

    @staticmethod
    def _expression(cron: str) -> str:
        minute, hour, dom, month, dow = cron.split()[:5]
        # EventBridge cron needs '?' in either day-of-month or day-of-week and has a year field.
        if dow != "*":
            dom = "?"
        else:
            dow = "?"
        return f"cron({minute} {hour} {dom} {month} {dow} *)"

    async def upsert_schedule(self, name: str, cron: str, task: str, payload: dict[str, Any]) -> None:
        args = {
            "Name": name[:64],
            "GroupName": self.group,
            "ScheduleExpression": self._expression(cron),
            "ScheduleExpressionTimezone": "Australia/Sydney",
            "FlexibleTimeWindow": {"Mode": "FLEXIBLE", "MaximumWindowInMinutes": 15},
            "Target": {
                "Arn": self.target_queue_arn,
                "RoleArn": self.role_arn,
                "Input": json.dumps({"task": task, "payload": payload}),
            },
            "State": "ENABLED",
        }
        try:
            await asyncio.to_thread(self._client.update_schedule, **args)
        except self._client.exceptions.ResourceNotFoundException:
            await asyncio.to_thread(self._client.create_schedule, **args)

    async def delete_schedule(self, name: str) -> None:
        try:
            await asyncio.to_thread(self._client.delete_schedule, Name=name[:64], GroupName=self.group)
        except self._client.exceptions.ResourceNotFoundException:
            return
