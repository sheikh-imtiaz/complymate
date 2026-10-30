from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.container import Container
from complymate.db.models import Notification
from complymate.domain.notifications.service import EMAIL_KINDS
from complymate.ports.queue import QueueName


async def notify(
    session: AsyncSession,
    container: Container,
    *,
    tenant_id: UUID,
    user_ids: list[UUID],
    kind: str,
    title: str,
    body: str | None = None,
    link: str | None = None,
) -> None:
    rows = [
        Notification(tenant_id=tenant_id, user_id=u, kind=kind, title=title, body=body, link=link)
        for u in set(user_ids)
    ]
    session.add_all(rows)
    await session.flush()
    if kind in EMAIL_KINDS:
        for n in rows:
            await container.queue.send(
                QueueName.NOTIFICATIONS,
                {
                    "task": "send_notification_email",
                    "payload": {"tenant_id": str(tenant_id), "notification_id": str(n.id)},
                },
            )
