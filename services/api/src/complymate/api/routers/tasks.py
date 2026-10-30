from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from complymate.api.deps import Ctx, require
from complymate.db.models import Task
from complymate.db.repositories.tasks import TaskRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden, NotFound
from complymate.domain.rbac.permissions import P
from complymate.schemas.tasks import TaskCreate, TaskOut, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])
MANAGERS = {"owner", "amlco", "senior_manager"}


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    scope: str = "mine", status: str | None = "open", ctx: Ctx = Depends(require(P.TASK_READ))
) -> list[object]:
    repo = TaskRepo(ctx.session)
    if scope == "all" and ctx.principal.role_key in MANAGERS:
        return list(await repo.list(status=status))
    return list(await repo.list(assignee_id=ctx.user_id, status=status))


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(body: TaskCreate, ctx: Ctx = Depends(require(P.TASK_UPDATE))) -> object:
    task = await ctx.tasks.create(
        ctx.tenant_id,
        "general",
        body.title,
        assignee_id=body.assignee_id or ctx.user_id,
        created_by=ctx.user_id,
        description=body.description,
        due=body.due_date,
        resource_type=body.resource_type,
        resource_id=body.resource_id,
    )
    await ctx.record(Action.CREATE, "task", task.id, after={"title": body.title})
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(task_id: UUID, body: TaskUpdate, ctx: Ctx = Depends(require(P.TASK_UPDATE))) -> object:
    task = await ctx.session.get(Task, task_id)
    if task is None:
        raise NotFound("task not found")
    if task.assignee_id != ctx.user_id and task.created_by != ctx.user_id and ctx.principal.role_key not in MANAGERS:
        raise Forbidden("you can only update your own tasks")
    changes = body.model_dump(exclude_unset=True)
    before = {k: getattr(task, k) for k in changes}
    for k, v in changes.items():
        setattr(task, k, v)
    if changes.get("status") == "done":
        task.completed_at, task.completed_by = datetime.now(UTC), ctx.user_id
    if changes.get("assignee_id"):
        await ctx.tasks.notify(
            ctx.tenant_id, changes["assignee_id"], "task_assigned", f"Task assigned: {task.title}", link="/tasks"
        )
    await ctx.record(
        Action.UPDATE,
        "task",
        task.id,
        before={k: str(v) for k, v in before.items()},
        after={k: str(v) for k, v in changes.items()},
    )
    return task
