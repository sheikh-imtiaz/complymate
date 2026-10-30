"""Azure Container Apps Jobs (cron trigger). Each schedule is a job running the worker image with `job <task>`."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from complymate.adapters.azure._credential import sync_credential


class ContainerJobsScheduler:
    def __init__(
        self, subscription_id: str, resource_group: str, environment_id: str, image: str, location: str
    ) -> None:
        from azure.mgmt.appcontainers import ContainerAppsAPIClient

        self.resource_group = resource_group
        self.environment_id = environment_id
        self.image = image
        self.location = location
        self._client = ContainerAppsAPIClient(sync_credential(), subscription_id)

    def _job(self, cron: str, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "location": self.location,
            "environment_id": self.environment_id,
            "identity": {"type": "SystemAssigned"},
            "configuration": {
                "trigger_type": "Schedule",
                "replica_timeout": 1800,
                "replica_retry_limit": 1,
                "schedule_trigger_config": {"cron_expression": cron, "parallelism": 1, "replica_completion_count": 1},
            },
            "template": {
                "containers": [
                    {
                        "name": "worker",
                        "image": self.image,
                        "args": ["job", task, json.dumps(payload)],
                        "resources": {"cpu": 0.5, "memory": "1Gi"},
                    }
                ]
            },
        }

    async def upsert_schedule(self, name: str, cron: str, task: str, payload: dict[str, Any]) -> None:
        job_name = name.lower().replace("_", "-")[:32]
        poller = await asyncio.to_thread(
            self._client.jobs.begin_create_or_update, self.resource_group, job_name, self._job(cron, task, payload)
        )
        await asyncio.to_thread(poller.result)

    async def delete_schedule(self, name: str) -> None:
        job_name = name.lower().replace("_", "-")[:32]
        poller = await asyncio.to_thread(self._client.jobs.begin_delete, self.resource_group, job_name)
        await asyncio.to_thread(poller.result)
