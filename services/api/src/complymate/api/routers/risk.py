from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends

from complymate.api.access import load_client
from complymate.api.deps import Ctx, require
from complymate.application import risk as risk_service
from complymate.db.models import EddTask, RiskAssessment
from complymate.db.repositories.clients import ClientRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import scope_for
from complymate.schemas.risk import AssessmentOut, EddTaskOut, EddTaskUpdate, OverrideIn

router = APIRouter(tags=["risk"])


@router.post("/clients/{client_id}/risk", response_model=AssessmentOut, status_code=201)
async def run_assessment(client_id: UUID, ctx: Ctx = Depends(require(P.RISK_CREATE))) -> object:
    ctx.scope = scope_for(ctx.principal, P.CLIENT_READ) or ctx.scope
    client = await load_client(ctx, client_id)
    assessment = await risk_service.assess(ctx.session, client, ctx.user_id)
    if assessment.level == "high":
        approvers = [
            u.id
            for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("senior_manager", "amlco", "owner"))
            if u.id != ctx.user_id
        ]
        for uid in approvers[:2]:
            await ctx.tasks.create(
                ctx.tenant_id,
                "approval",
                f"High-risk client needs second approval: {client.display_name}",
                assignee_id=uid,
                created_by=ctx.user_id,
                resource_type="client",
                resource_id=str(client.id),
                link=f"/clients/{client.id}/risk",
            )
    await ctx.record(
        Action.CREATE,
        "risk_assessment",
        assessment.id,
        after={
            "client_id": str(client.id),
            "level": assessment.level,
            "score": assessment.score,
            "rules_version": assessment.rules_version,
        },
    )
    return assessment


@router.get("/clients/{client_id}/risk", response_model=list[AssessmentOut])
async def list_assessments(client_id: UUID, ctx: Ctx = Depends(require(P.RISK_READ))) -> list[object]:
    await load_client(ctx, client_id)
    return list(await ClientRepo(ctx.session).assessments(client_id))


@router.post("/clients/{client_id}/risk/{assessment_id}/override", response_model=AssessmentOut)
async def override(
    client_id: UUID, assessment_id: UUID, body: OverrideIn, ctx: Ctx = Depends(require(P.RISK_UPDATE))
) -> object:
    client = await load_client(ctx, client_id)
    assessment = await ctx.session.get(RiskAssessment, assessment_id)
    if assessment is None or assessment.client_id != client_id:
        raise NotFound("assessment not found")
    before = {"level": assessment.override_level or assessment.level}
    assessment.override_level = body.level
    assessment.override_reason = body.reason
    # An override to high is a high-risk decision: it needs a second person (status back to proposed).
    assessment.status = "proposed" if body.level == "high" else "approved"
    client.risk_level = body.level
    await ctx.record(
        Action.UPDATE, "risk_assessment", assessment.id, before=before, after={"level": body.level}, reason=body.reason
    )
    return assessment


@router.get("/clients/{client_id}/edd-tasks", response_model=list[EddTaskOut])
async def list_edd(client_id: UUID, ctx: Ctx = Depends(require(P.RISK_READ))) -> list[object]:
    await load_client(ctx, client_id)
    return list(await ClientRepo(ctx.session).edd_tasks(client_id))


@router.patch("/edd-tasks/{task_id}", response_model=EddTaskOut)
async def update_edd(task_id: UUID, body: EddTaskUpdate, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))) -> object:
    task = await ctx.session.get(EddTask, task_id)
    if task is None:
        raise NotFound("EDD task not found")
    await load_client(ctx, task.client_id)
    before = {"status": task.status}
    task.status = body.status
    task.evidence = {**(task.evidence or {}), **body.evidence, **({"note": body.note} if body.note else {})}
    if body.status in ("done", "waived"):
        task.completed_by = ctx.user_id
        task.completed_at = datetime.now(UTC)
    await ctx.record(Action.UPDATE, "edd_task", task.id, before=before, after={"status": body.status}, reason=body.note)
    return task
