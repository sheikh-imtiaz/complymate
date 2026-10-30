from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Notification, Task
from complymate.domain.tasks.service import default_due


class TaskRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def create(
        self,
        tenant_id: UUID,
        type_: str,
        title: str,
        *,
        assignee_id: UUID | None,
        created_by: UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        due: date | None = None,
        link: str | None = None,
    ) -> Task:
        task = Task(
            tenant_id=tenant_id,
            type=type_,
            title=title,
            description=description,
            assignee_id=assignee_id,
            created_by=created_by,
            resource_type=resource_type,
            resource_id=resource_id,
            due_date=due or default_due(type_),
        )
        self.s.add(task)
        if assignee_id:
            self.s.add(
                Notification(
                    tenant_id=tenant_id,
                    user_id=assignee_id,
                    kind="task_assigned",
                    title=f"New task: {title}",
                    body=description,
                    link=link or "/tasks",
                )
            )
        await self.s.flush()
        return task

    async def list(self, *, assignee_id: UUID | None = None, status: str | None = "open") -> Sequence[Task]:
        stmt = select(Task)
        if assignee_id:
            stmt = stmt.where(Task.assignee_id == assignee_id)
        if status:
            stmt = stmt.where(Task.status == status)
        return (await self.s.execute(stmt.order_by(Task.due_date.asc().nulls_last(), Task.created_at))).scalars().all()

    async def open_for_resource(self, resource_type: str, resource_id: str, type_: str | None = None) -> Sequence[Task]:
        stmt = select(Task).where(
            Task.resource_type == resource_type, Task.resource_id == resource_id, Task.status == "open"
        )
        if type_:
            stmt = stmt.where(Task.type == type_)
        return (await self.s.execute(stmt)).scalars().all()

    async def notify(
        self, tenant_id: UUID, user_id: UUID, kind: str, title: str, body: str | None = None, link: str | None = None
    ) -> Notification:
        n = Notification(tenant_id=tenant_id, user_id=user_id, kind=kind, title=title, body=body, link=link)
        self.s.add(n)
        await self.s.flush()
        return n
