from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.application.exports import save_export
from complymate.application.notify import notify
from complymate.db.models import QuizAttempt, Tenant, TrainingAssignment, TrainingModule, User
from complymate.db.repositories.training import TrainingRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden, NotFound
from complymate.domain.programs.export import html_to_pdf
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import Scope
from complymate.domain.training.service import certificate_html, grade, is_overdue
from complymate.schemas.training import (
    AssignmentIn,
    AssignmentOut,
    AttemptIn,
    AttemptOut,
    AttemptResult,
    ModuleDetail,
    ModuleOut,
    QuestionPublic,
)

router = APIRouter(prefix="/training", tags=["training"])


async def _jurisdiction(ctx: Ctx) -> str:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    return tenant.jurisdiction if tenant else "AU"


@router.get("/modules", response_model=list[ModuleOut])
async def modules(ctx: Ctx = Depends(require(P.TRAINING_READ))) -> list[object]:
    return list(await TrainingRepo(ctx.session).modules(await _jurisdiction(ctx)))


@router.get("/modules/{module_id}", response_model=ModuleDetail)
async def module(module_id: UUID, ctx: Ctx = Depends(require(P.TRAINING_READ))) -> ModuleDetail:
    repo = TrainingRepo(ctx.session)
    m = await repo.visible_module(module_id)
    if m is None:
        raise NotFound("module not found")
    questions = await repo.approved_questions(module_id)
    return ModuleDetail(
        **ModuleOut.model_validate(m).model_dump(),
        content_md=m.content_md,
        questions=[QuestionPublic(id=q.id, question=q.question, options=q.options) for q in questions],
    )


@router.post("/modules/{module_id}/attempts", response_model=AttemptResult, status_code=201)
async def attempt(module_id: UUID, body: AttemptIn, ctx: Ctx = Depends(require(P.TRAINING_READ))) -> AttemptResult:
    repo = TrainingRepo(ctx.session)
    m = await repo.visible_module(module_id)
    if m is None:
        raise NotFound("module not found")
    questions = [q.to_dict() for q in await repo.approved_questions(module_id)]
    result = grade(questions, body.answers, m.pass_mark)
    att = QuizAttempt(
        tenant_id=ctx.tenant_id,
        module_id=module_id,
        user_id=ctx.user_id,
        answers=body.answers,
        score=result.percent,
        passed=result.passed,
    )
    ctx.session.add(att)
    await ctx.session.flush()
    if result.passed:
        assignment = await repo.assignment(module_id, ctx.user_id)
        if assignment and not assignment.completed_at:
            assignment.completed_at = datetime.now(UTC)
        tenant = await ctx.session.get(Tenant, ctx.tenant_id)
        user = await ctx.session.get(User, ctx.user_id)
        html = certificate_html(
            tenant.name if tenant else "",
            (user.full_name or user.email) if user else "",
            m.title,
            date.today(),
            result.percent,
        )
        pdf = await asyncio.to_thread(html_to_pdf, html)
        export = await save_export(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            kind="training_certificate",
            filename=f"certificate-{m.title}.pdf",
            content_type="application/pdf",
            data=pdf,
            created_by=ctx.user_id,
        )
        att.certificate_key = str(export.id)
    await ctx.record(
        Action.CREATE,
        "quiz_attempt",
        att.id,
        after={"module_id": str(module_id), "score": result.percent, "passed": result.passed},
    )
    return AttemptResult(attempt=AttemptOut.model_validate(att), feedback=result.feedback)


@router.get("/my")
async def my_training(ctx: Ctx = Depends(require(P.TRAINING_READ))) -> dict[str, object]:
    repo = TrainingRepo(ctx.session)
    assignments = await repo.assignments(ctx.user_id)
    attempts = await repo.attempts(ctx.user_id)
    return {
        "assignments": [
            {
                **AssignmentOut.model_validate(a).model_dump(),
                "overdue": is_overdue(a.due_date, a.completed_at is not None),
            }
            for a in assignments
        ],
        "attempts": [AttemptOut.model_validate(a).model_dump() for a in attempts],
    }


@router.get("/status")
async def completion_status(ctx: Ctx = Depends(require(P.TRAINING_READ))) -> list[dict[str, object]]:
    if ctx.scope is not Scope.ALL:
        raise Forbidden("you can only see your own training results")
    members = await UserRepo(ctx.session).members(ctx.tenant_id)
    assignments = await TrainingRepo(ctx.session).assignments()
    by_user: dict[UUID, list[TrainingAssignment]] = {}
    for a in assignments:
        by_user.setdefault(a.user_id, []).append(a)
    return [
        {
            "user_id": m["user_id"],
            "full_name": m["full_name"],
            "role": m["role_key"],
            "assigned": len(by_user.get(m["user_id"], [])),
            "completed": sum(1 for a in by_user.get(m["user_id"], []) if a.completed_at),
            "overdue": sum(
                1 for a in by_user.get(m["user_id"], []) if is_overdue(a.due_date, a.completed_at is not None)
            ),
        }
        for m in members
        if m["status"] == "active"
    ]


@router.post("/assignments", response_model=list[AssignmentOut], status_code=201)
async def assign(body: AssignmentIn, ctx: Ctx = Depends(require(P.TRAINING_CREATE))) -> list[object]:
    repo = TrainingRepo(ctx.session)
    if await repo.visible_module(body.module_id) is None:
        raise NotFound("module not found")
    out: list[object] = []
    for uid in body.user_ids:
        existing = await repo.assignment(body.module_id, uid)
        if existing:
            existing.due_date = body.due_date
            out.append(existing)
            continue
        a = TrainingAssignment(tenant_id=ctx.tenant_id, module_id=body.module_id, user_id=uid, due_date=body.due_date)
        ctx.session.add(a)
        out.append(a)
    await ctx.session.flush()
    await notify(
        ctx.session,
        ctx.container,
        tenant_id=ctx.tenant_id,
        user_ids=body.user_ids,
        kind="training_assigned",
        title="New training assigned",
        link="/training",
    )
    await ctx.record(Action.CREATE, "training_assignment", body.module_id, after={"users": len(body.user_ids)})
    return out


@router.get("/certificates/{attempt_id}")
async def certificate(attempt_id: UUID, ctx: Ctx = Depends(require(P.TRAINING_READ))) -> Response:
    from complymate.db.models import Export

    att = await ctx.session.get(QuizAttempt, attempt_id)
    if att is None or (att.user_id != ctx.user_id and ctx.scope is not Scope.ALL) or not att.certificate_key:
        raise NotFound("certificate not found")
    export = await ctx.session.get(Export, UUID(att.certificate_key))
    assert export is not None
    obj = await ctx.container.storage.get_object(ctx.container.settings.exports_bucket, export.storage_key)
    return Response(
        obj.data,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{export.filename}"'},
    )


@router.get("/modules-all", response_model=list[ModuleOut])
async def tenant_modules(ctx: Ctx = Depends(require(P.TRAINING_UPDATE))) -> list[object]:
    """Firm-specific modules plus published platform modules (for assignment screens)."""
    stmt = select(TrainingModule).order_by(TrainingModule.title)
    return list((await ctx.session.execute(stmt)).scalars().all())
