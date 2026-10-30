"""Screens one client (queued after onboarding or by the nightly job)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from complymate.application.notify import notify
from complymate.application.screening import screen_client
from complymate.container import get_container
from complymate.db.models import Client
from complymate.db.repositories.tasks import TaskRepo
from complymate.db.repositories.users import UserRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.workers._common import system_audit


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    async with tenant_session(tenant_id) as session:
        client = await session.get(Client, UUID(payload["client_id"]))
        if client is None or client.status in ("declined", "exited"):
            return {"status": "skipped"}
        run_, matches = await screen_client(session, client, trigger=payload.get("trigger", "nightly"), actor_id=None)
        if matches:
            officers = [u.id for u in await UserRepo(session).users_with_role(tenant_id, ("amlco",))]
            await notify(
                session,
                get_container(),
                tenant_id=tenant_id,
                user_ids=officers,
                kind="screening_match",
                title=f"Re-screening found {len(matches)} possible match(es) for {client.display_name}",
                link="/screening",
            )
            for uid in officers:
                await TaskRepo(session).create(
                    tenant_id,
                    "rescreen_match",
                    f"Review re-screening match: {client.display_name}",
                    assignee_id=uid,
                    resource_type="client",
                    resource_id=str(client.id),
                    link="/screening",
                )
        await system_audit(
            session,
            tenant_id,
            Action.SCREEN,
            "client",
            client.id,
            after={"run_id": str(run_.id), "matches": len(matches), "trigger": run_.trigger},
        )
        return {"status": "done", "matches": len(matches)}
