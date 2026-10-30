"""Worker entrypoint. The queue adapter (SQS / Service Bus / in-memory) calls `dispatch(task, payload)`.

python -m complymate.workers.entry --task refresh_watchlists '{}'   # one-off (Container Apps Job)
python -m complymate.workers.entry --serve                           # long-running (local cron / Service Bus)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

import structlog

from complymate.workers import (
    archive_audit_events,
    build_regulator_pack,
    draft_program,
    nightly_rescreen,
    ocr_document,
    refresh_watchlists,
    screen_client,
    seed_reference,
    send_reminders,
    send_scheduled_reports,
    verify_audit_chain,
)

log = structlog.get_logger(__name__)
Handler = Callable[[dict[str, Any]], Awaitable[Any]]


async def migrate(payload: dict[str, Any]) -> dict[str, Any]:
    """Runs Alembic as the owner role. On AWS the passwords come from Secrets Manager."""
    from alembic import command
    from alembic.config import Config

    from complymate.container import get_container

    container = get_container()
    s = container.settings
    if s.db_secret_arn and not os.environ.get("APP_DB_PASSWORD"):
        os.environ["APP_DB_PASSWORD"] = (await container.secrets.get_json(s.db_secret_arn))["password"]
    if not os.environ.get("DATABASE_ADMIN_URL"):
        os.environ["DATABASE_ADMIN_URL"] = await container.database_url(admin=True)
    cfg = Config(os.environ.get("ALEMBIC_INI", "/app/alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(os.path.dirname(cfg.config_file_name or "."), "migrations"))
    await asyncio.to_thread(command.upgrade, cfg, payload.get("revision", "head"))
    return {"status": "migrated"}


async def run_evals(payload: dict[str, Any]) -> dict[str, Any]:
    """Nightly model evals (nightly-evals.yml invokes the worker Lambda so it runs inside the VPC)."""
    from uuid import UUID

    from complymate.agent.evals.run_evals import run

    return await run(UUID(payload["tenant_id"]), float(payload.get("min_score", 0.85)))


TASKS: dict[str, Handler] = {
    "run_evals": run_evals,
    "migrate": migrate,
    "seed_reference": seed_reference.run,
    "ocr_document": ocr_document.run,
    "screen_client": screen_client.run,
    "nightly_rescreen": nightly_rescreen.run,
    "refresh_watchlists": refresh_watchlists.run,
    "draft_program_section": draft_program.run_section,
    "draft_program_finalize": draft_program.finalize,
    "workflow:program_draft": draft_program.run_workflow,
    "build_regulator_pack": build_regulator_pack.run,
    "workflow:regulator_pack": build_regulator_pack.run,
    "send_reminders": send_reminders.run,
    "program_review_reminder": send_reminders.program_review,
    "send_notification_email": send_reminders.send_notification_email,
    "send_invite_email": send_reminders.send_invite_email,
    "send_scheduled_reports": send_scheduled_reports.run,
    "verify_audit_chain": verify_audit_chain.run,
    "archive_audit_events": archive_audit_events.run,
}

# Default schedules (EventBridge Scheduler in Terraform; local cron / Container Apps Jobs elsewhere). Sydney time.
DEFAULT_SCHEDULES = {
    "refresh-watchlists": ("0 1 * * *", "refresh_watchlists"),
    "nightly-rescreen": ("0 2 * * *", "nightly_rescreen"),
    "verify-audit-chain": ("30 2 * * *", "verify_audit_chain"),
    "archive-audit-events": ("*/15 * * * *", "archive_audit_events"),
    "send-reminders": ("0 7 * * *", "send_reminders"),
}


async def dispatch(task: str, payload: dict[str, Any]) -> Any:
    handler = TASKS.get(task)
    if handler is None:
        raise KeyError(f"unknown task {task}")
    log.info("worker.task_start", task=task)
    result = await handler(payload or {})
    log.info("worker.task_done", task=task)
    return result


async def serve() -> None:
    """Local / Azure long-running worker: evaluates cron schedules every minute (and consumes Service Bus on Azure)."""
    from complymate.adapters.local.cron_scheduler import CronScheduler
    from complymate.container import get_container

    container = get_container()
    cron = container.scheduler if isinstance(container.scheduler, CronScheduler) else CronScheduler()
    # On Azure, Container Apps Jobs run the schedules (RUN_SCHEDULES=false); locally this loop does.
    if os.environ.get("RUN_SCHEDULES", "true").lower() == "true":
        for name, (expr, task) in DEFAULT_SCHEDULES.items():
            await cron.upsert_schedule(name, expr, task, {})
    consumers = []
    if container.settings.cloud_provider == "azure":
        consumers.append(asyncio.create_task(_consume_servicebus()))
    log.info("worker.serving", schedules=len(cron.schedules))
    while True:
        now = datetime.now(UTC).replace(second=0, microsecond=0)
        for s in cron.due(now):
            try:
                await dispatch(s.task, s.payload)
            except Exception:
                log.exception("worker.scheduled_failed", task=s.task)
        await asyncio.sleep(60 - datetime.now(UTC).second)


async def _consume_servicebus() -> None:
    from azure.servicebus.aio import ServiceBusClient

    from complymate.adapters.azure._credential import async_credential
    from complymate.container import get_container
    from complymate.ports.queue import QueueName

    ns = get_container().settings.azure_servicebus_namespace
    async with ServiceBusClient(f"{ns}.servicebus.windows.net", credential=async_credential()) as client:

        async def consume(queue: str) -> None:
            async with client.get_queue_receiver(queue) as receiver:
                async for msg in receiver:
                    try:
                        body = json.loads(str(msg))
                        await dispatch(body["task"], body.get("payload", {}))
                        await receiver.complete_message(msg)
                    except Exception:
                        log.exception("servicebus.message_failed", queue=queue)
                        await receiver.abandon_message(msg)

        await asyncio.gather(*(consume(q.value) for q in QueueName))


def main() -> None:
    from complymate.config import get_settings
    from complymate.observability.logging import configure_logging

    configure_logging(get_settings().log_level)
    parser = argparse.ArgumentParser()
    parser.add_argument("--task")
    parser.add_argument("payload", nargs="?", default="{}")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--local", action="store_true", help="alias for --serve")
    args = parser.parse_args()
    if args.task:
        print(json.dumps(asyncio.run(dispatch(args.task, json.loads(args.payload))), default=str))
    else:
        asyncio.run(serve())


if __name__ == "__main__":
    main()
