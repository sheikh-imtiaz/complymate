"""Nightly re-screening of all active clients. Fans out one queue message per client."""

from __future__ import annotations

from typing import Any

from complymate.container import get_container
from complymate.db.repositories.clients import ClientRepo
from complymate.db.session import tenant_session
from complymate.observability import metrics
from complymate.ports.queue import QueueName
from complymate.workers._common import active_tenant_ids


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    container = get_container()
    queued = 0
    try:
        for tenant_id in await active_tenant_ids():
            async with tenant_session(tenant_id) as session:
                ids = await ClientRepo(session).active_ids()
            for client_id in ids:
                await container.queue.send(
                    QueueName.SCREENING,
                    {
                        "task": "screen_client",
                        "payload": {"tenant_id": str(tenant_id), "client_id": str(client_id), "trigger": "nightly"},
                    },
                )
                queued += 1
    except Exception:
        metrics.screening_job_failed("nightly_rescreen")
        raise
    return {"queued": queued}
