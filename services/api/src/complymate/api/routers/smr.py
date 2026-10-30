"""Suspicious Matter Reporting. Strict access: drafts by staff, everything else AMLCO / Owner / Senior Manager.
The tipping-off warning is returned with every read."""

from __future__ import annotations

import io
import time
import zipfile
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from complymate.agent.factory import complete_json, load_prompt
from complymate.api.deps import Ctx, require
from complymate.application import llm_usage
from complymate.application.notify import notify
from complymate.db.models import Client, SmrCase, SmrNote, Tenant
from complymate.db.repositories.smr import SmrRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden, NotFound, ValidationFailed
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import scope_for
from complymate.domain.smr import service as smr
from complymate.schemas.smr import SmrCreate, SmrDecisionIn, SmrDetail, SmrNoteIn, SmrNoteOut, SmrOut, SmrUpdate

router = APIRouter(prefix="/smr", tags=["smr"])


def _full_access(ctx: Ctx) -> bool:
    return scope_for(ctx.principal, P.SMR_READ) is not None


async def _case(ctx: Ctx, case_id: UUID) -> SmrCase:
    case = await ctx.session.get(SmrCase, case_id)
    if case is None:
        raise NotFound("case not found")
    if not _full_access(ctx) and case.raised_by != ctx.user_id:
        raise NotFound("case not found")
    return case


@router.get("", response_model=list[SmrOut])
async def list_cases(status: str | None = None, ctx: Ctx = Depends(require(P.SMR_CREATE_DRAFT))) -> list[object]:
    repo = SmrRepo(ctx.session)
    if _full_access(ctx):
        return list(await repo.list(status=status))
    return list(await repo.list(raised_by=ctx.user_id, status=status))


@router.post("", response_model=SmrOut, status_code=201)
async def raise_concern(body: SmrCreate, ctx: Ctx = Depends(require(P.SMR_CREATE_DRAFT))) -> object:
    repo = SmrRepo(ctx.session)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    case = SmrCase(
        tenant_id=ctx.tenant_id,
        reference=await repo.next_reference(),
        client_id=body.client_id,
        status="draft",
        raised_by=ctx.user_id,
        assigned_to=tenant.amlco_user_id if tenant else None,
        summary=body.summary,
        transaction_details=body.transaction_details,
    )
    ctx.session.add(case)
    await ctx.session.flush()
    await ctx.record(Action.CREATE, "smr_case", case.id, after={"reference": case.reference})
    return case


@router.get("/{case_id}", response_model=SmrDetail)
async def get_case(case_id: UUID, ctx: Ctx = Depends(require(P.SMR_CREATE_DRAFT))) -> SmrDetail:
    case = await _case(ctx, case_id)
    notes = await SmrRepo(ctx.session).notes(case.id) if _full_access(ctx) else []
    await ctx.record(Action.VIEW_SENSITIVE, "smr_case", case.id)
    return SmrDetail(
        case=SmrOut.model_validate(case),
        notes=[SmrNoteOut.model_validate(n) for n in notes],
        tipping_off_warning=smr.TIPPING_OFF_WARNING,
    )


@router.post("/{case_id}/submit", response_model=SmrOut)
async def submit_for_review(case_id: UUID, ctx: Ctx = Depends(require(P.SMR_CREATE_DRAFT))) -> object:
    case = await _case(ctx, case_id)
    if case.raised_by != ctx.user_id and not _full_access(ctx):
        raise Forbidden("only the person who raised the concern can submit it")
    smr.assert_transition(case.status, "under_review")
    case.status = "under_review"
    officers = [u.id for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("amlco",))] or (
        [case.assigned_to] if case.assigned_to else []
    )
    for uid in officers:
        await ctx.tasks.create(
            ctx.tenant_id,
            "smr",
            f"Review internal concern {case.reference}",
            assignee_id=uid,
            created_by=ctx.user_id,
            resource_type="smr_case",
            resource_id=str(case.id),
            link=f"/smr/{case.id}",
        )
    await ctx.record(Action.SUBMIT, "smr_case", case.id, after={"status": case.status})
    return case


@router.patch("/{case_id}", response_model=SmrOut)
async def update_case(case_id: UUID, body: SmrUpdate, ctx: Ctx = Depends(require(P.SMR_UPDATE))) -> object:
    case = await _case(ctx, case_id)
    if case.status in ("decided_no_report", "exported"):
        raise ValidationFailed("case is closed")
    changes = body.model_dump(exclude_unset=True)
    if bad := set(changes.get("suspicion_categories") or []) - set(smr.SUSPICION_CATEGORIES):
        raise ValidationFailed(f"unknown categories: {sorted(bad)}")
    for k, v in changes.items():
        setattr(case, k, v)
    await ctx.record(Action.UPDATE, "smr_case", case.id, after={"fields": sorted(changes)})
    return case


@router.post("/{case_id}/notes", response_model=SmrNoteOut, status_code=201)
async def add_note(case_id: UUID, body: SmrNoteIn, ctx: Ctx = Depends(require(P.SMR_UPDATE))) -> object:
    case = await _case(ctx, case_id)
    note = SmrNote(tenant_id=ctx.tenant_id, case_id=case.id, author_id=ctx.user_id, body=body.body)
    ctx.session.add(note)
    await ctx.session.flush()
    await ctx.record(Action.CREATE, "smr_note", note.id, after={"case_id": str(case.id)})
    return note


@router.post("/{case_id}/ai-assist", response_model=SmrOut)
async def ai_assist(case_id: UUID, ctx: Ctx = Depends(require(P.SMR_UPDATE))) -> object:
    """The agent structures facts into report fields. It never decides and never submits."""
    case = await _case(ctx, case_id)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    notes = await SmrRepo(ctx.session).notes(case.id)
    system = load_prompt("smr_helper").format(
        jurisdiction=tenant.jurisdiction if tenant else "AU",
        categories=smr.SUSPICION_CATEGORIES,
        fields=smr.AUSTRAC_FIELDS,
    )
    user = f"Case summary:\n{case.summary}\n\nTransaction details:\n{case.transaction_details}\n\nNotes:\n" + "\n".join(
        f"- {n.body}" for n in notes
    )
    start = time.perf_counter()
    parsed, result = await complete_json(ctx.container.llm, system, user, fast=False)
    await llm_usage.record(
        ctx.session,
        ctx.container.settings,
        tenant_id=ctx.tenant_id,
        purpose="smr_helper",
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
    case.ai_suggestion = parsed if isinstance(parsed, dict) else {"raw": parsed}
    await ctx.record(
        Action.AI_SUGGESTION,
        "smr_case",
        case.id,
        ai={"model": result.model, "prompt_version": ctx.container.settings.prompt_version, "purpose": "smr_helper"},
    )
    return case


@router.post("/{case_id}/decide", response_model=SmrOut)
async def decide(case_id: UUID, body: SmrDecisionIn, ctx: Ctx = Depends(require(P.SMR_APPROVE))) -> object:
    case = await _case(ctx, case_id)
    new_status = "decided_report" if body.report else "decided_no_report"
    smr.assert_transition(case.status, new_status)
    if body.report and not (case.grounds or "").strip():
        raise ValidationFailed("record the grounds for suspicion before deciding to report")
    case.status = new_status
    case.decision_reason = body.reason
    case.decided_by = ctx.user_id
    case.decided_at = datetime.now(UTC)
    for task in await ctx.tasks.open_for_resource("smr_case", str(case.id)):
        task.status, task.completed_at, task.completed_by = "done", datetime.now(UTC), ctx.user_id
    if body.report:
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            user_ids=[ctx.user_id],
            kind="smr_deadline",
            title=f"{case.reference}: lodge with AUSTRAC within the deadline",
            body="24 hours for terrorism financing, 3 business days otherwise.",
            link=f"/smr/{case.id}",
        )
    await ctx.record(Action.DECIDE, "smr_case", case.id, after={"status": new_status}, reason=body.reason)
    return case


@router.get("/{case_id}/export")
async def export(case_id: UUID, ctx: Ctx = Depends(require(P.SMR_EXPORT))) -> Response:
    case = await _case(ctx, case_id)
    if case.status not in ("decided_report", "exported"):
        raise ValidationFailed("only cases decided for reporting can be exported")
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    client = await ctx.session.get(Client, case.client_id) if case.client_id else None
    payload = smr.austrac_export(
        case.to_dict(),
        tenant.to_dict() if tenant else {},
        {"display_name": client.display_name, "date_of_birth": client.date_of_birth} if client else None,
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in smr.export_files(payload).items():
            zf.writestr(name, data)
    case.status = "exported"
    case.exported_at = datetime.now(UTC)
    await ctx.record(Action.EXPORT, "smr_case", case.id, after={"format": "austrac-manual"})
    return Response(
        buf.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{case.reference}.zip"', "Cache-Control": "no-store"},
    )
