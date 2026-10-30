"""Daily reminders: ongoing-CDD review tasks, task escalation to the AMLCO, overdue training alerts."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select

from complymate.application.notify import notify
from complymate.container import get_container
from complymate.db.models import Program, Task, Tenant, TrainingAssignment
from complymate.db.repositories.clients import ClientRepo
from complymate.db.repositories.tasks import TaskRepo
from complymate.db.session import tenant_session
from complymate.domain.risk.rules_loader import load_rules
from complymate.domain.tasks.service import needs_escalation
from complymate.domain.training.service import is_overdue
from complymate.workers._common import active_tenant_ids


async def _tenant(tenant_id: UUID) -> dict[str, int]:
    container = get_container()
    stats = {"review_tasks": 0, "escalated": 0, "training_alerts": 0}
    async with tenant_session(tenant_id) as session:
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            return stats
        rules = load_rules(tenant.jurisdiction)
        tasks = TaskRepo(session)
        horizon = date.today() + timedelta(days=rules.reminder_days_before)
        for client in await ClientRepo(session).reviews_due(horizon):
            if await tasks.open_for_resource("client", str(client.id), "review"):
                continue
            await tasks.create(
                tenant_id,
                "review",
                f"Ongoing CDD review due: {client.display_name}",
                assignee_id=client.assigned_to or tenant.amlco_user_id,
                resource_type="client",
                resource_id=str(client.id),
                due=client.next_review_date,
                link=f"/clients/{client.id}",
            )
            stats["review_tasks"] += 1

        open_tasks = (await session.execute(select(Task).where(Task.status == "open"))).scalars().all()
        for task in open_tasks:
            if needs_escalation(task.due_date, task.status, task.escalated_at is not None) and tenant.amlco_user_id:
                task.escalated_at = datetime.now(UTC)
                await notify(
                    session,
                    container,
                    tenant_id=tenant_id,
                    user_ids=[tenant.amlco_user_id],
                    kind="task_escalated",
                    title=f"Overdue task escalated: {task.title}",
                    link="/tasks",
                )
                stats["escalated"] += 1

        assignments = (
            (await session.execute(select(TrainingAssignment).where(TrainingAssignment.completed_at.is_(None))))
            .scalars()
            .all()
        )
        for a in assignments:
            if is_overdue(a.due_date, False) and (
                a.reminded_at is None or a.reminded_at < datetime.now(UTC) - timedelta(days=7)
            ):
                a.reminded_at = datetime.now(UTC)
                await notify(
                    session,
                    container,
                    tenant_id=tenant_id,
                    user_ids=[a.user_id],
                    kind="training_overdue",
                    title="Your AML/CTF training is overdue",
                    link=f"/training/{a.module_id}",
                )
                stats["training_alerts"] += 1
    return stats


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    totals: dict[str, int] = {}
    for tenant_id in await active_tenant_ids():
        for k, v in (await _tenant(tenant_id)).items():
            totals[k] = totals.get(k, 0) + v
    return totals


async def program_review(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    async with tenant_session(tenant_id) as session:
        tenant = await session.get(Tenant, tenant_id)
        program = (await session.execute(select(Program))).scalar_one_or_none()
        if tenant is None or program is None or not tenant.amlco_user_id:
            return {"status": "skipped"}
        await TaskRepo(session).create(
            tenant_id,
            "program_review",
            "Annual AML/CTF program review is due",
            assignee_id=tenant.amlco_user_id,
            resource_type="program",
            resource_id=str(program.id),
            link="/program",
        )
    return {"status": "created"}


async def send_notification_email(payload: dict[str, Any]) -> dict[str, Any]:
    from complymate.db.models import Notification, User
    from complymate.workers._common import render

    container = get_container()
    tenant_id = UUID(payload["tenant_id"])
    async with tenant_session(tenant_id) as session:
        n = await session.get(Notification, UUID(payload["notification_id"]))
        if n is None or n.emailed_at:
            return {"status": "skipped"}
        user = await session.get(User, n.user_id)
        tenant = await session.get(Tenant, tenant_id)
        if user is None:
            return {"status": "skipped"}
        html = render(
            "emails/reminder.html",
            title=n.title,
            body=n.body or "",
            firm=tenant.name if tenant else "",
            link=f"{container.settings.web_base_url}{n.link or '/'}",
        )
        await container.email.send([user.email], n.title, html, text=f"{n.title}\n\n{n.body or ''}")
        n.emailed_at = datetime.now(UTC)
    return {"status": "sent"}


async def send_invite_email(payload: dict[str, Any]) -> dict[str, Any]:
    from complymate.db.models import Invitation
    from complymate.workers._common import render

    container = get_container()
    tenant_id = UUID(payload["tenant_id"])
    async with tenant_session(tenant_id) as session:
        inv = await session.get(Invitation, UUID(payload["invitation_id"]))
        tenant = await session.get(Tenant, tenant_id)
        if inv is None or tenant is None:
            return {"status": "skipped"}
        html = render(
            "emails/invite.html",
            firm=tenant.name,
            name=inv.full_name or "",
            link=payload["accept_url"],
            expires=inv.expires_at.date().isoformat(),
        )
        await container.email.send([inv.email], f"You're invited to {tenant.name} on ComplyMate", html)
    return {"status": "sent"}
