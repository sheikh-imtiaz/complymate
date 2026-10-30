from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from complymate.api.deps import Ctx, require
from complymate.application.notify import notify
from complymate.db.models import (
    PresenceHeartbeat,
    Program,
    ProgramApproval,
    ProgramSection,
    ProgramVersion,
    Tenant,
    TenantSettings,
    User,
)
from complymate.db.repositories.programs import ProgramRepo
from complymate.db.repositories.users import UserRepo
from complymate.domain.audit.events import Action
from complymate.domain.collaboration.presence import cutoff
from complymate.domain.errors import Conflict, NotFound, ValidationFailed
from complymate.domain.programs import approval
from complymate.domain.programs.export import ExportProgram, ExportSection, safe_filename, to_docx, to_pdf
from complymate.domain.programs.interview import QUESTIONS, SECTION_KEYS, progress
from complymate.domain.programs.service import assert_lock, compare_versions, new_lock, tracked_change
from complymate.domain.rbac.permissions import P
from complymate.domain.risk.rules_loader import load_rules
from complymate.schemas.common import Ok
from complymate.schemas.programs import (
    AiDecisionIn,
    ApprovalOut,
    CompareSection,
    DecisionIn,
    DraftRequest,
    InterviewOut,
    InterviewSave,
    NewVersionIn,
    PresenceOut,
    ProgramOut,
    QuestionOut,
    RiskMethodologyIn,
    SectionOut,
    SectionUpdate,
    VersionDetail,
    VersionSummary,
)

router = APIRouter(prefix="/program", tags=["program"])


async def _program(ctx: Ctx) -> Program:
    return await ProgramRepo(ctx.session).ensure(ctx.tenant_id, ctx.user_id)


async def _version(ctx: Ctx, version_id: UUID) -> ProgramVersion:
    version = await ProgramRepo(ctx.session).version(version_id)
    if version is None:
        raise NotFound("program version not found")
    return version


def _state(v: ProgramVersion) -> approval.VersionState:
    return approval.VersionState(v.status, v.created_by, v.submitted_by, v.reviewed_by, v.locked)


@router.get("", response_model=ProgramOut)
async def get_program(ctx: Ctx = Depends(require(P.PROGRAM_READ))) -> ProgramOut:
    program = await _program(ctx)
    versions = await ProgramRepo(ctx.session).versions(program.id)
    return ProgramOut(
        id=program.id,
        status=program.status,
        current_version_id=program.current_version_id,
        approved_version_id=program.approved_version_id,
        next_review_due=program.next_review_due,
        interview_progress=progress(program.interview_answers or {}),
        versions=[VersionSummary.model_validate(v) for v in versions],
        risk_methodology=program.risk_methodology or {},
    )


@router.get("/interview", response_model=InterviewOut)
async def get_interview(ctx: Ctx = Depends(require(P.PROGRAM_READ))) -> InterviewOut:
    program = await _program(ctx)
    return InterviewOut(
        questions=[
            QuestionOut(
                id=q.id, text=q.text, kind=q.kind, sections=list(q.sections), options=list(q.options), help=q.help
            )
            for q in QUESTIONS
        ],
        answers=program.interview_answers or {},
        progress=progress(program.interview_answers or {}),
    )


@router.put("/interview", response_model=InterviewOut)
async def save_interview(body: InterviewSave, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> InterviewOut:
    program = await _program(ctx)
    valid = {q.id for q in QUESTIONS}
    unknown = set(body.answers) - valid
    if unknown:
        raise ValidationFailed(f"unknown questions: {sorted(unknown)}")
    program.interview_answers = {**(program.interview_answers or {}), **body.answers}
    await ctx.record(Action.UPDATE, "program_interview", program.id, after={"answered": sorted(body.answers)})
    return await get_interview(ctx)


@router.put("/risk-methodology", response_model=ProgramOut)
async def save_methodology(body: RiskMethodologyIn, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> ProgramOut:
    program = await _program(ctx)
    before = program.risk_methodology
    program.risk_methodology = body.model_dump()
    await ctx.record(
        Action.UPDATE, "program_risk_methodology", program.id, before=before, after=program.risk_methodology
    )
    return await get_program(ctx)


@router.post("/draft", response_model=VersionSummary, status_code=202)
async def start_draft(body: DraftRequest, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> ProgramVersion:
    """Starts the agent drafting workflow (Step Functions on AWS): one task per section, with citations."""
    program = await _program(ctx)
    version = await _version(ctx, program.current_version_id)  # type: ignore[arg-type]
    if version.locked:
        raise Conflict("current version is approved; create a new version first")
    if progress(program.interview_answers or {}) < 0.5:
        raise ValidationFailed("answer at least half of the interview questions first")
    sections = body.sections or SECTION_KEYS
    if bad := set(sections) - set(SECTION_KEYS):
        raise ValidationFailed(f"unknown sections: {sorted(bad)}")
    version.draft_status = "queued"
    payload = {
        "tenant_id": str(ctx.tenant_id),
        "version_id": str(version.id),
        "sections": sections,
        "requested_by": str(ctx.user_id),
    }
    await ctx.container.workflows.start("program_draft", payload)
    await ctx.record(
        Action.AI_SUGGESTION,
        "program_version",
        version.id,
        after={"sections": sections},
        ai={"workflow": "program_draft", "prompt_version": ctx.container.settings.prompt_version},
    )
    return version


@router.get("/versions/{version_id}", response_model=VersionDetail)
async def get_version(version_id: UUID, ctx: Ctx = Depends(require(P.PROGRAM_READ))) -> VersionDetail:
    version = await _version(ctx, version_id)
    repo = ProgramRepo(ctx.session)
    return VersionDetail(
        **VersionSummary.model_validate(version).model_dump(),
        sections=[SectionOut.model_validate(s) for s in await repo.sections(version.id)],
        approvals=[ApprovalOut.model_validate(a) for a in await repo.approvals(version.id)],
    )


async def _section(ctx: Ctx, version: ProgramVersion, key: str) -> ProgramSection:
    section = await ProgramRepo(ctx.session).section(version.id, key)
    if section is None:
        raise NotFound("section not found")
    return section


@router.post("/versions/{version_id}/sections/{key}/lock", response_model=SectionOut)
async def lock_section(version_id: UUID, key: str, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> ProgramSection:
    version = await _version(ctx, version_id)
    if version.locked:
        raise Conflict("version is locked")
    section = await _section(ctx, version, key)
    assert_lock(section.locked_by, section.locked_until, ctx.user_id)
    section.locked_by = ctx.user_id
    section.locked_until = new_lock()
    return section


@router.delete("/versions/{version_id}/sections/{key}/lock", response_model=Ok)
async def unlock_section(version_id: UUID, key: str, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> Ok:
    section = await _section(ctx, await _version(ctx, version_id), key)
    if section.locked_by == ctx.user_id:
        section.locked_by = None
        section.locked_until = None
    return Ok()


@router.put("/versions/{version_id}/sections/{key}", response_model=SectionOut)
async def update_section(
    version_id: UUID, key: str, body: SectionUpdate, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))
) -> ProgramSection:
    from complymate.agent.guardrails import sanitize_html

    version = await _version(ctx, version_id)
    if version.locked or version.status not in ("draft",):
        raise Conflict("only draft versions can be edited")
    section = await _section(ctx, version, key)
    assert_lock(section.locked_by, section.locked_until, ctx.user_id)
    if body.expected_updated_at and section.updated_at and section.updated_at > body.expected_updated_at:
        raise Conflict("section changed since you opened it; reload to see the latest text")
    new_html = sanitize_html(body.content_html)
    change = tracked_change(section.content_html, new_html, ctx.user_id)
    section.tracked_changes = [*(section.tracked_changes or []), change][-50:]
    section.content_html = new_html
    section.updated_by = ctx.user_id
    section.updated_at = datetime.now(UTC)
    section.locked_until = new_lock()
    section.locked_by = ctx.user_id
    await ctx.record(
        Action.UPDATE,
        "program_section",
        section.id,
        after={"key": key, "added": change["added"], "removed": change["removed"]},
    )
    return section


@router.post("/versions/{version_id}/sections/{key}/ai-decision", response_model=SectionOut)
async def ai_decision(
    version_id: UUID, key: str, body: AiDecisionIn, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))
) -> ProgramSection:
    version = await _version(ctx, version_id)
    section = await _section(ctx, version, key)
    if not section.ai_draft_html:
        raise ValidationFailed("no AI draft to decide on")
    if version.locked:
        raise Conflict("version is locked")
    if body.accept:
        change = tracked_change(section.content_html, section.ai_draft_html, ctx.user_id, ai=True)
        section.tracked_changes = [*(section.tracked_changes or []), change][-50:]
        section.content_html = section.ai_draft_html
        section.ai_generated = True
        section.updated_by = ctx.user_id
        section.updated_at = datetime.now(UTC)
    section.ai_accepted = body.accept
    section.ai_draft_html = None
    await ctx.record(
        Action.AI_ACCEPTED if body.accept else Action.AI_REJECTED,
        "program_section",
        section.id,
        ai={
            "sources": [c.get("title") for c in section.citations or []],
            "decision": body.accept,
            "prompt_version": ctx.container.settings.prompt_version,
        },
    )
    return section


@router.post("/versions/{version_id}/submit", response_model=VersionSummary)
async def submit(version_id: UUID, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> ProgramVersion:
    version = await _version(ctx, version_id)
    sections = await ProgramRepo(ctx.session).sections(version.id)
    empty = [s.title for s in sections if not s.content_html.strip()]
    if empty:
        raise ValidationFailed(f"complete all sections first: {', '.join(empty[:3])}")
    if any(s.ai_draft_html for s in sections):
        raise ValidationFailed("accept or reject all AI suggestions first")
    state = approval.submit_for_review(_state(version), ctx.user_id)
    version.status, version.submitted_by, version.submitted_at = state.status, state.submitted_by, datetime.now(UTC)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    reviewers = [u.id for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("amlco",))]
    if not reviewers and tenant and tenant.amlco_user_id:
        reviewers = [tenant.amlco_user_id]
    for uid in reviewers:
        await ctx.tasks.create(
            ctx.tenant_id,
            "approval",
            f"Review AML/CTF program v{version.version_number}",
            assignee_id=uid,
            created_by=ctx.user_id,
            resource_type="program_version",
            resource_id=str(version.id),
            link=f"/program/{version.id}",
        )
    await ctx.record(Action.SUBMIT, "program_version", version.id, after={"status": version.status})
    return version


async def _decide(ctx: Ctx, version: ProgramVersion, step: str, body: DecisionIn) -> None:
    ctx.session.add(
        ProgramApproval(
            tenant_id=ctx.tenant_id,
            version_id=version.id,
            step=step,
            decision="approved" if body.approve else "rejected",
            decided_by=ctx.user_id,
            decided_role=ctx.principal.role_key or "",
            comment=body.comment,
            decided_at=datetime.now(UTC),
        )
    )
    for task in await ctx.tasks.open_for_resource("program_version", str(version.id), "approval"):
        task.status, task.completed_at, task.completed_by = "done", datetime.now(UTC), ctx.user_id


@router.post("/versions/{version_id}/review", response_model=VersionSummary)
async def amlco_review(
    version_id: UUID, body: DecisionIn, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))
) -> ProgramVersion:
    version = await _version(ctx, version_id)
    state = approval.amlco_review(_state(version), ctx.user_id, ctx.principal.role_key or "", body.approve)
    version.status, version.reviewed_by = state.status, state.reviewed_by
    await _decide(ctx, version, "amlco_review", body)
    if body.approve:
        signers = [
            u.id
            for u in await UserRepo(ctx.session).users_with_role(ctx.tenant_id, ("owner", "senior_manager"))
            if u.id != version.submitted_by
        ]
        for uid in signers:
            await ctx.tasks.create(
                ctx.tenant_id,
                "approval",
                f"Sign off AML/CTF program v{version.version_number}",
                assignee_id=uid,
                created_by=ctx.user_id,
                resource_type="program_version",
                resource_id=str(version.id),
                link=f"/program/{version.id}",
            )
    elif version.submitted_by:
        await notify(
            ctx.session,
            ctx.container,
            tenant_id=ctx.tenant_id,
            user_ids=[version.submitted_by],
            kind="approval_requested",
            title="Program returned for changes",
            body=body.comment,
            link=f"/program/{version.id}",
        )
    await ctx.record(
        Action.APPROVE if body.approve else Action.REJECT,
        "program_version",
        version.id,
        after={"step": "amlco_review", "status": version.status},
        reason=body.comment,
    )
    return version


@router.post("/versions/{version_id}/sign-off", response_model=VersionSummary)
async def sign_off(
    version_id: UUID, body: DecisionIn, ctx: Ctx = Depends(require(P.PROGRAM_APPROVE))
) -> ProgramVersion:
    version = await _version(ctx, version_id)
    state = approval.sign_off(_state(version), ctx.user_id, ctx.principal.role_key or "", body.approve)
    version.status, version.locked = state.status, state.locked
    await _decide(ctx, version, "sign_off", body)
    program = await _program(ctx)
    if body.approve:
        repo = ProgramRepo(ctx.session)
        for v in await repo.versions(program.id):
            if v.id != version.id and v.status == "approved":
                v.status = "superseded"
        version.approved_by, version.approved_at = ctx.user_id, datetime.now(UTC)
        version.snapshot = {
            "sections": [
                {"key": s.key, "title": s.title, "content_html": s.content_html, "citations": s.citations}
                for s in await repo.sections(version.id)
            ]
        }
        tenant = await ctx.session.get(Tenant, ctx.tenant_id)
        rules = load_rules(tenant.jurisdiction if tenant else "AU")
        program.status = "approved"
        program.approved_version_id = version.id
        today = date.today()
        program.next_review_due = date(today.year + rules.program_review_months // 12, today.month, min(today.day, 28))
        await ctx.container.scheduler.upsert_schedule(
            f"program-review-{ctx.tenant_id}",
            f"0 9 {min(today.day, 28)} {today.month} *",
            "program_review_reminder",
            {"tenant_id": str(ctx.tenant_id)},
        )
    await ctx.record(
        Action.APPROVE if body.approve else Action.REJECT,
        "program_version",
        version.id,
        after={"step": "sign_off", "status": version.status, "locked": version.locked},
        reason=body.comment,
    )
    return version


@router.post("/versions", response_model=VersionSummary, status_code=201)
async def new_version(body: NewVersionIn, ctx: Ctx = Depends(require(P.PROGRAM_UPDATE))) -> ProgramVersion:
    program = await _program(ctx)
    repo = ProgramRepo(ctx.session)
    current = await repo.version(program.current_version_id) if program.current_version_id else None
    if current and not current.locked:
        raise Conflict("finish or discard the current draft first")
    version = await repo.new_version(program, ctx.user_id, current)
    version.change_summary = body.change_summary
    program.current_version_id = version.id
    await ctx.record(
        Action.CREATE,
        "program_version",
        version.id,
        after={"version": version.version_number, "change_summary": body.change_summary},
    )
    return version


@router.get("/versions/{a}/compare/{b}", response_model=list[CompareSection])
async def compare(a: UUID, b: UUID, ctx: Ctx = Depends(require(P.PROGRAM_READ))) -> list[dict[str, object]]:
    repo = ProgramRepo(ctx.session)
    va, vb = await _version(ctx, a), await _version(ctx, b)
    sa = [{"key": s.key, "title": s.title, "content_html": s.content_html} for s in await repo.sections(va.id)]
    sb = [{"key": s.key, "title": s.title, "content_html": s.content_html} for s in await repo.sections(vb.id)]
    return compare_versions(sa, sb)


@router.get("/versions/{version_id}/export")
async def export(
    version_id: UUID, format: str = Query("docx", pattern="^(docx|pdf)$"), ctx: Ctx = Depends(require(P.PROGRAM_EXPORT))
) -> Response:
    version = await _version(ctx, version_id)
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    settings = await ctx.session.get(TenantSettings, ctx.tenant_id)
    branding = settings.branding if settings else {}
    logo = None
    if branding.get("logo_key"):
        logo = (
            await ctx.container.storage.get_object(ctx.container.settings.exports_bucket, branding["logo_key"])
        ).data
    approver = await ctx.session.get(User, version.approved_by) if version.approved_by else None
    sections = await ProgramRepo(ctx.session).sections(version.id)
    program = ExportProgram(
        firm_name=tenant.name if tenant else "Firm",
        version_number=version.version_number,
        status=version.status,
        approved_at=version.approved_at.date().isoformat() if version.approved_at else None,
        approved_by=approver.full_name if approver else None,
        sections=[ExportSection(s.title, s.content_html, s.citations) for s in sections],
        logo=logo,
        primary_color=branding.get("primary_color", "#0F4C81"),
    )
    import asyncio

    if format == "pdf":
        data, media = await asyncio.to_thread(to_pdf, program), "application/pdf"
    else:
        template = f"{ctx.container.settings.templates_dir}/program.docx"
        data = await asyncio.to_thread(to_docx, program, template)
        media = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    filename = safe_filename(f"{program.firm_name}-AML-CTF-Program-v{version.version_number}.{format}")
    await ctx.record(Action.EXPORT, "program_version", version.id, after={"format": format})
    return Response(data, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/versions/{version_id}/presence", response_model=list[PresenceOut])
async def heartbeat(version_id: UUID, ctx: Ctx = Depends(require(P.PROGRAM_READ))) -> list[PresenceOut]:
    stmt = (
        insert(PresenceHeartbeat)
        .values(
            tenant_id=ctx.tenant_id,
            resource_type="program_version",
            resource_id=str(version_id),
            user_id=ctx.user_id,
            last_seen_at=datetime.now(UTC),
        )
        .on_conflict_do_update(
            index_elements=["tenant_id", "resource_type", "resource_id", "user_id"],
            set_={"last_seen_at": datetime.now(UTC)},
        )
    )
    await ctx.session.execute(stmt)
    rows = (
        await ctx.session.execute(
            select(PresenceHeartbeat, User.full_name)
            .join(User, User.id == PresenceHeartbeat.user_id)
            .where(
                PresenceHeartbeat.resource_type == "program_version",
                PresenceHeartbeat.resource_id == str(version_id),
                PresenceHeartbeat.last_seen_at >= cutoff(),
            )
        )
    ).all()
    return [PresenceOut(user_id=h.user_id, full_name=name, last_seen_at=h.last_seen_at) for h, name in rows]
