"""Platform Admin API (vendor staff). Separate app/domain in the frontend; every action goes to the platform
audit chain (tenant_id NULL). Platform context never exposes client ID documents, parties or SMRs (RLS)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import func, select

from complymate.agent.factory import complete_json, load_prompt
from complymate.agent.rag.ingest import ingest_source
from complymate.agent.rag.retriever import Retriever, format_sources
from complymate.api.deps import Ctx, require_platform
from complymate.application import llm_usage
from complymate.db.models import (
    AiFeedback,
    ChainVerification,
    ChatMessage,
    FeatureFlag,
    ImpersonationSession,
    KbSource,
    LlmCall,
    QuizQuestion,
    Tenant,
    TrainingModule,
    WatchlistVersion,
)
from complymate.db.repositories.audit import AuditRepo
from complymate.db.repositories.kb import KbRepo
from complymate.db.repositories.tenants import TenantRepo
from complymate.db.repositories.training import TrainingRepo
from complymate.db.session import apply_context
from complymate.domain.audit.events import Action
from complymate.domain.billing.usage import period
from complymate.domain.errors import Forbidden, NotFound, ValidationFailed
from complymate.domain.platform.feature_flags import DEFAULT_FLAGS
from complymate.domain.platform.impersonation import validate_request
from complymate.domain.rbac.permissions import P
from complymate.schemas.audit import AuditEventOut
from complymate.schemas.common import Ok
from complymate.schemas.platform_admin import (
    FeedbackResolveIn,
    FlagIn,
    GenerateQuizIn,
    HealthOut,
    ImpersonationOut,
    ImpersonationRequestIn,
    KbSourceIn,
    KbSourceOut,
    LastCheckedIn,
    TenantStatusIn,
    TenantSummary,
)
from complymate.schemas.training import ModuleOut, ModuleUpsert, QuizQuestionOut, QuizReviewIn

router = APIRouter(prefix="/platform", tags=["platform-admin"])


def _need(ctx: Ctx, permission: str) -> None:
    if permission not in ctx.principal.permissions:
        raise Forbidden(f"missing permission {permission}")


async def _platform_audit(ctx: Ctx, action: str, resource_type: str, resource_id: Any, **kw: Any) -> None:
    await ctx.audit.record(ctx.audit_ctx, action, resource_type, resource_id, tenant_id=None, **kw)


# ---------------- tenants ----------------


@router.get("/tenants", response_model=list[TenantSummary])
async def tenants(
    status: str | None = None, q: str | None = None, ctx: Ctx = Depends(require_platform)
) -> list[TenantSummary]:
    _need(ctx, P.PLATFORM_TENANTS_READ)
    repo = TenantRepo(ctx.session)
    out = []
    for t in await repo.list_all(status, q):
        sub = await repo.subscription(t.id)
        out.append(
            TenantSummary(
                id=t.id,
                name=t.name,
                jurisdiction=t.jurisdiction,
                status=t.status,
                plan_code=t.plan_code,
                created_at=t.created_at,
                members=await repo.member_count(t.id),
                usage=await repo.usage(t.id, period()),
                subscription_status=sub.status if sub else None,
            )
        )
    return out


@router.get("/tenants/{tenant_id}")
async def tenant_detail(tenant_id: UUID, ctx: Ctx = Depends(require_platform)) -> dict[str, Any]:
    _need(ctx, P.PLATFORM_TENANTS_READ)
    repo = TenantRepo(ctx.session)
    tenant = await repo.get(tenant_id)
    if tenant is None:
        raise NotFound("tenant not found")
    sub = await repo.subscription(tenant_id)
    g, t = await repo.flags(tenant_id)
    llm = (
        await ctx.session.execute(
            select(func.coalesce(func.sum(LlmCall.cost_usd), 0)).where(
                LlmCall.tenant_id == tenant_id, LlmCall.created_at >= datetime.now(UTC).replace(day=1)
            )
        )
    ).scalar_one()
    return {
        "tenant": {k: v for k, v in tenant.to_dict().items()},
        "subscription": sub.to_dict() if sub else None,
        "members": await repo.member_count(tenant_id),
        "usage": await repo.usage(tenant_id, period()),
        "flags": {**DEFAULT_FLAGS, **g, **t},
        "tenant_flag_overrides": t,
        "llm_cost_month_usd": float(llm),
    }


async def _set_status(ctx: Ctx, tenant_id: UUID, status: str, reason: str) -> Ok:
    _need(ctx, P.PLATFORM_TENANTS_UPDATE)
    tenant = await TenantRepo(ctx.session).get(tenant_id)
    if tenant is None:
        raise NotFound("tenant not found")
    before = tenant.status
    tenant.status = status
    await _platform_audit(
        ctx, Action.UPDATE, "tenant", tenant_id, before={"status": before}, after={"status": status}, reason=reason
    )
    return Ok()


@router.post("/tenants/{tenant_id}/suspend", response_model=Ok)
async def suspend(tenant_id: UUID, body: TenantStatusIn, ctx: Ctx = Depends(require_platform)) -> Ok:
    return await _set_status(ctx, tenant_id, "suspended", body.reason)


@router.post("/tenants/{tenant_id}/reactivate", response_model=Ok)
async def reactivate(tenant_id: UUID, body: TenantStatusIn, ctx: Ctx = Depends(require_platform)) -> Ok:
    return await _set_status(ctx, tenant_id, "active", body.reason)


# ---------------- feature flags ----------------


@router.get("/feature-flags")
async def flags(ctx: Ctx = Depends(require_platform)) -> dict[str, Any]:
    _need(ctx, P.PLATFORM_TENANTS_READ)
    rows = (await ctx.session.execute(select(FeatureFlag))).scalars().all()
    return {
        "defaults": DEFAULT_FLAGS,
        "global": {f.key: f.enabled for f in rows if f.tenant_id is None},
        "tenants": [{"tenant_id": str(f.tenant_id), "key": f.key, "enabled": f.enabled} for f in rows if f.tenant_id],
    }


@router.put("/feature-flags", response_model=Ok)
async def set_flag(body: FlagIn, ctx: Ctx = Depends(require_platform)) -> Ok:
    _need(ctx, P.PLATFORM_FLAGS_UPDATE)
    if body.key not in DEFAULT_FLAGS:
        raise ValidationFailed("unknown flag")
    existing = (
        await ctx.session.execute(
            select(FeatureFlag).where(
                FeatureFlag.key == body.key,
                FeatureFlag.tenant_id == body.tenant_id if body.tenant_id else FeatureFlag.tenant_id.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.enabled, existing.updated_by, existing.updated_at = body.enabled, ctx.user_id, datetime.now(UTC)
    else:
        ctx.session.add(
            FeatureFlag(key=body.key, tenant_id=body.tenant_id, enabled=body.enabled, updated_by=ctx.user_id)
        )
    await _platform_audit(
        ctx,
        Action.UPDATE,
        "feature_flag",
        body.key,
        after={"enabled": body.enabled, "tenant_id": str(body.tenant_id) if body.tenant_id else None},
    )
    return Ok()


# ---------------- knowledge base ----------------


def _kb_out(s: KbSource) -> KbSourceOut:
    return KbSourceOut(
        id=s.id,
        jurisdiction=s.jurisdiction,
        title=s.title,
        url=s.url,
        publisher=s.publisher,
        status=s.status,
        chunk_count=s.chunk_count,
        last_checked_at=s.last_checked_at,
        indexed_at=s.indexed_at,
    )


@router.get("/kb/sources", response_model=list[KbSourceOut])
async def kb_sources(ctx: Ctx = Depends(require_platform)) -> list[KbSourceOut]:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    return [_kb_out(s) for s in await KbRepo(ctx.session).sources()]


@router.post("/kb/sources", response_model=KbSourceOut, status_code=201)
async def add_kb_source(body: KbSourceIn, ctx: Ctx = Depends(require_platform)) -> KbSourceOut:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    source = KbSource(
        jurisdiction=body.jurisdiction,
        title=body.title,
        url=body.url,
        publisher=body.publisher,
        doc_type=body.doc_type,
        last_checked_at=datetime.now(UTC),
    )
    ctx.session.add(source)
    await ctx.session.flush()
    key = f"kb/{source.id}.txt"
    await ctx.container.storage.put_object(
        ctx.container.settings.exports_bucket, key, body.content.encode(), "text/plain"
    )
    source.storage_key = key
    await ingest_source(ctx.session, ctx.container.embeddings, source, body.content)
    await _platform_audit(
        ctx, Action.CREATE, "kb_source", source.id, after={"title": body.title, "chunks": source.chunk_count}
    )
    return _kb_out(source)


@router.post("/kb/sources/{source_id}/reindex", response_model=KbSourceOut)
async def reindex(source_id: UUID, ctx: Ctx = Depends(require_platform)) -> KbSourceOut:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    source = await ctx.session.get(KbSource, source_id)
    if source is None or not source.storage_key:
        raise NotFound("source not found")
    text = (
        await ctx.container.storage.get_object(ctx.container.settings.exports_bucket, source.storage_key)
    ).data.decode()
    await ingest_source(ctx.session, ctx.container.embeddings, source, text, force=True)
    await _platform_audit(
        ctx, Action.UPDATE, "kb_source", source.id, after={"reindexed": True, "chunks": source.chunk_count}
    )
    return _kb_out(source)


@router.patch("/kb/sources/{source_id}/last-checked", response_model=KbSourceOut)
async def set_last_checked(source_id: UUID, body: LastCheckedIn, ctx: Ctx = Depends(require_platform)) -> KbSourceOut:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    source = await ctx.session.get(KbSource, source_id)
    if source is None:
        raise NotFound("source not found")
    source.last_checked_at = body.last_checked_at or datetime.now(UTC)
    await _platform_audit(
        ctx, Action.UPDATE, "kb_source", source.id, after={"last_checked_at": source.last_checked_at.isoformat()}
    )
    return _kb_out(source)


@router.post("/kb/sources/{source_id}/archive", response_model=KbSourceOut)
async def archive_source(source_id: UUID, ctx: Ctx = Depends(require_platform)) -> KbSourceOut:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    source = await ctx.session.get(KbSource, source_id)
    if source is None:
        raise NotFound("source not found")
    source.status = "archived"
    await _platform_audit(ctx, Action.UPDATE, "kb_source", source.id, after={"status": "archived"})
    return _kb_out(source)


# ---------------- templates (training modules) & quizzes ----------------


@router.get("/templates", response_model=list[ModuleOut])
async def templates(ctx: Ctx = Depends(require_platform)) -> list[object]:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    stmt = select(TrainingModule).where(TrainingModule.tenant_id.is_(None)).order_by(TrainingModule.title)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("/templates", response_model=ModuleOut, status_code=201)
async def create_template(body: ModuleUpsert, ctx: Ctx = Depends(require_platform)) -> object:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    module = TrainingModule(tenant_id=None, **body.model_dump())
    ctx.session.add(module)
    await ctx.session.flush()
    await _platform_audit(ctx, Action.CREATE, "training_module", module.id, after={"title": body.title})
    return module


@router.put("/templates/{module_id}", response_model=ModuleOut)
async def update_template(module_id: UUID, body: ModuleUpsert, ctx: Ctx = Depends(require_platform)) -> object:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    module = await ctx.session.get(TrainingModule, module_id)
    if module is None or module.tenant_id is not None:
        raise NotFound("module not found")
    if body.status == "published":
        approved = (
            await ctx.session.execute(
                select(func.count()).where(
                    QuizQuestion.module_id == module_id, QuizQuestion.review_status == "approved"
                )
            )
        ).scalar_one()
        if approved == 0:
            raise ValidationFailed("approve at least one quiz question before publishing")
    for k, v in body.model_dump().items():
        setattr(module, k, v)
    module.version += 1
    await _platform_audit(
        ctx, Action.UPDATE, "training_module", module.id, after={"status": body.status, "version": module.version}
    )
    return module


@router.get("/quizzes", response_model=list[QuizQuestionOut])
async def quizzes(
    module_id: UUID | None = None, review_status: str | None = None, ctx: Ctx = Depends(require_platform)
) -> list[object]:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    return list(await TrainingRepo(ctx.session).questions(module_id, review_status))


@router.post("/quizzes/generate", response_model=list[QuizQuestionOut], status_code=201)
async def generate_quiz(body: GenerateQuizIn, ctx: Ctx = Depends(require_platform)) -> list[object]:
    """Agent-generated questions from the rule library; they start as drafts for Content Manager review."""
    import time

    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    module = await ctx.session.get(TrainingModule, body.module_id)
    if module is None:
        raise NotFound("module not found")
    chunks = await Retriever(ctx.session, ctx.container.embeddings).search(
        f"{module.title} {module.description or ''}", module.jurisdiction, k=6
    )
    system = load_prompt("quiz_writer").format(
        roles=", ".join(module.roles) or "all staff",
        jurisdiction=module.jurisdiction,
        count=body.count,
        module_title=module.title,
    )
    start = time.perf_counter()
    items, result = await complete_json(ctx.container.llm, system, f"Sources:\n{format_sources(chunks)}")
    await llm_usage.record(
        ctx.session,
        ctx.container.settings,
        tenant_id=None,
        purpose="quiz_writer",
        model=result.model,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        latency_ms=int((time.perf_counter() - start) * 1000),
    )
    created: list[object] = []
    for item in items if isinstance(items, list) else []:
        try:
            ref = int(str(item.get("source", "S1")).lstrip("S")) - 1
            src = chunks[ref] if 0 <= ref < len(chunks) else None
            q = QuizQuestion(
                module_id=module.id,
                question=item["question"],
                options=list(item["options"])[:4],
                correct_index=int(item["correct_index"]),
                explanation=item.get("explanation"),
                source_citation={"title": src.title, "url": src.url} if src else None,
                review_status="draft",
                ai_generated=True,
            )
        except (KeyError, ValueError, TypeError):
            continue
        ctx.session.add(q)
        created.append(q)
    await ctx.session.flush()
    await _platform_audit(
        ctx,
        Action.AI_SUGGESTION,
        "quiz_questions",
        module.id,
        after={"created": len(created)},
        ai={"model": result.model, "purpose": "quiz_writer"},
    )
    return created


@router.patch("/quizzes/{question_id}", response_model=QuizQuestionOut)
async def review_question(question_id: UUID, body: QuizReviewIn, ctx: Ctx = Depends(require_platform)) -> object:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    q = await ctx.session.get(QuizQuestion, question_id)
    if q is None:
        raise NotFound("question not found")
    if body.review_status not in ("draft", "approved", "rejected"):
        raise ValidationFailed("invalid review status")
    for field in ("question", "options", "correct_index", "explanation"):
        if (value := getattr(body, field)) is not None:
            setattr(q, field, value)
    if not 0 <= q.correct_index < len(q.options):
        raise ValidationFailed("correct_index out of range")
    q.review_status = body.review_status
    q.reviewed_by = ctx.user_id
    action = (
        Action.AI_ACCEPTED
        if body.review_status == "approved"
        else Action.AI_REJECTED
        if body.review_status == "rejected"
        else Action.UPDATE
    )
    await _platform_audit(ctx, action, "quiz_question", q.id, after={"review_status": q.review_status})
    return q


# ---------------- usage & AI quality ----------------


@router.get("/usage-costs")
async def usage_costs(ctx: Ctx = Depends(require_platform)) -> dict[str, Any]:
    _need(ctx, P.PLATFORM_USAGE_READ)
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    rows = (
        await ctx.session.execute(
            select(
                LlmCall.tenant_id,
                Tenant.name,
                LlmCall.purpose,
                func.count(),
                func.sum(LlmCall.input_tokens),
                func.sum(LlmCall.output_tokens),
                func.sum(LlmCall.cost_usd),
            )
            .outerjoin(Tenant, Tenant.id == LlmCall.tenant_id)
            .where(LlmCall.created_at >= month_start)
            .group_by(LlmCall.tenant_id, Tenant.name, LlmCall.purpose)
        )
    ).all()
    chat = (
        await ctx.session.execute(
            select(ChatMessage.tenant_id, func.count(), func.sum(ChatMessage.cost_usd))
            .where(ChatMessage.created_at >= month_start, ChatMessage.role == "assistant")
            .group_by(ChatMessage.tenant_id)
        )
    ).all()
    total = sum((r[6] or Decimal(0)) for r in rows) + sum((r[2] or Decimal(0)) for r in chat)
    return {
        "period": period(),
        "budget_usd": ctx.container.settings.llm_monthly_budget_usd,
        "total_usd": float(total),
        "by_tenant_purpose": [
            {
                "tenant_id": str(r[0]) if r[0] else None,
                "tenant": r[1] or "platform",
                "purpose": r[2],
                "calls": r[3],
                "input_tokens": int(r[4] or 0),
                "output_tokens": int(r[5] or 0),
                "cost_usd": float(r[6] or 0),
            }
            for r in rows
        ],
        "chat_by_tenant": [{"tenant_id": str(r[0]), "answers": r[1], "cost_usd": float(r[2] or 0)} for r in chat],
    }


@router.get("/ai-quality")
async def ai_quality(ctx: Ctx = Depends(require_platform)) -> dict[str, Any]:
    _need(ctx, P.PLATFORM_AI_QUALITY)
    flagged = (
        await ctx.session.execute(
            select(AiFeedback, ChatMessage)
            .join(ChatMessage, ChatMessage.id == AiFeedback.message_id)
            .where(AiFeedback.rating == "wrong")
            .order_by(AiFeedback.created_at.desc())
            .limit(100)
        )
    ).all()
    counts = dict(
        (await ctx.session.execute(select(AiFeedback.rating, func.count()).group_by(AiFeedback.rating))).all()
    )
    evals: Any = None
    try:
        import json

        obj = await ctx.container.storage.get_object(ctx.container.settings.exports_bucket, "evals/latest.json")
        evals = json.loads(obj.data)
    except Exception:
        evals = None
    return {
        "feedback_counts": counts,
        "helpful_rate": round(counts.get("helpful", 0) / max(1, sum(counts.values())), 3),
        "flagged": [
            {
                "feedback_id": str(f.id),
                "tenant_id": str(f.tenant_id),
                "comment": f.comment,
                "review_status": f.review_status,
                "answer": m.content[:2000],
                "citations": m.citations,
                "model": m.model,
                "prompt_version": m.prompt_version,
                "created_at": f.created_at.isoformat(),
            }
            for f, m in flagged
        ],
        "latest_eval": evals,
    }


@router.post("/ai-quality/feedback/{feedback_id}/resolve", response_model=Ok)
async def resolve_feedback(feedback_id: UUID, body: FeedbackResolveIn, ctx: Ctx = Depends(require_platform)) -> Ok:
    _need(ctx, P.PLATFORM_AI_QUALITY)
    fb = await ctx.session.get(AiFeedback, feedback_id)
    if fb is None:
        raise NotFound("feedback not found")
    fb.review_status, fb.resolution, fb.reviewed_by = "resolved", body.resolution, ctx.user_id
    await _platform_audit(ctx, Action.UPDATE, "ai_feedback", fb.id, after={"resolved": True})
    return Ok()


# ---------------- impersonation ----------------


@router.get("/impersonation", response_model=list[ImpersonationOut])
async def impersonations(ctx: Ctx = Depends(require_platform)) -> list[object]:
    _need(ctx, P.PLATFORM_IMPERSONATE)
    stmt = select(ImpersonationSession).order_by(ImpersonationSession.created_at.desc()).limit(100)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("/impersonation", response_model=ImpersonationOut, status_code=201)
async def request_impersonation(body: ImpersonationRequestIn, ctx: Ctx = Depends(require_platform)) -> object:
    _need(ctx, P.PLATFORM_IMPERSONATE)
    duration = validate_request(body.reason, body.minutes)
    tenant = await ctx.session.get(Tenant, body.tenant_id)
    if tenant is None:
        raise NotFound("tenant not found")
    imp = ImpersonationSession(
        tenant_id=body.tenant_id,
        support_user_id=ctx.user_id,
        reason=body.reason,
        duration_minutes=int(duration.total_seconds() // 60),
    )
    ctx.session.add(imp)
    await ctx.session.flush()
    # Notify the firm owner(s) to consent (tenant-scoped insert needs the tenant context).
    from complymate.db.models import Notification
    from complymate.db.repositories.users import UserRepo

    await apply_context(ctx.session, body.tenant_id, platform=True, user_id=ctx.user_id)
    for owner in await UserRepo(ctx.session).users_with_role(body.tenant_id, ("owner",)):
        ctx.session.add(
            Notification(
                tenant_id=body.tenant_id,
                user_id=owner.id,
                kind="support_access",
                title="ComplyMate support requests temporary access",
                body=body.reason,
                link="/admin/security",
            )
        )
    await ctx.audit.record(
        ctx.audit_ctx,
        Action.IMPERSONATION_START,
        "impersonation_session",
        imp.id,
        tenant_id=body.tenant_id,
        reason=body.reason,
        after={"requested_minutes": body.minutes},
    )
    await apply_context(ctx.session, None, platform=True, user_id=ctx.user_id)
    await _platform_audit(
        ctx,
        Action.IMPERSONATION_START,
        "impersonation_session",
        imp.id,
        reason=body.reason,
        after={"tenant_id": str(body.tenant_id), "status": "awaiting_consent"},
    )
    return imp


@router.post("/impersonation/{session_id}/end", response_model=Ok)
async def end_impersonation(session_id: UUID, ctx: Ctx = Depends(require_platform)) -> Ok:
    _need(ctx, P.PLATFORM_IMPERSONATE)
    imp = await ctx.session.get(ImpersonationSession, session_id)
    if imp is None or imp.support_user_id != ctx.user_id:
        raise NotFound("session not found")
    imp.ended_at = datetime.now(UTC)
    await _platform_audit(
        ctx, Action.IMPERSONATION_STOP, "impersonation_session", imp.id, after={"tenant_id": str(imp.tenant_id)}
    )
    return Ok()


# ---------------- system health & platform audit ----------------


@router.get("/system-health", response_model=HealthOut)
async def system_health(ctx: Ctx = Depends(require_platform)) -> HealthOut:
    _need(ctx, P.PLATFORM_HEALTH_READ)
    watchlists = (
        (await ctx.session.execute(select(WatchlistVersion).where(WatchlistVersion.is_current))).scalars().all()
    )
    stale_kb = (
        await ctx.session.execute(
            select(func.count()).where(
                KbSource.status == "active", KbSource.last_checked_at < datetime.now(UTC) - timedelta(days=90)
            )
        )
    ).scalar_one()
    jobs: dict[str, Any] = {
        "watchlists": [
            {
                "source": w.source,
                "label": w.version_label,
                "entries": w.entry_count,
                "fetched_at": w.fetched_at.isoformat(),
            }
            for w in watchlists
        ],
        "kb_sources_not_checked_90_days": stale_kb,
        "queues": "see CloudWatch dashboard (SQS depth, DLQ, Lambda errors)",
    }
    verifications = (
        (await ctx.session.execute(select(ChainVerification).order_by(ChainVerification.checked_at.desc()).limit(20)))
        .scalars()
        .all()
    )
    spend = (
        await ctx.session.execute(
            select(func.coalesce(func.sum(LlmCall.cost_usd), 0)).where(
                LlmCall.created_at >= datetime.now(UTC).replace(day=1)
            )
        )
    ).scalar_one()
    return HealthOut(
        database="ok",
        jobs=jobs,
        chain_verifications=[
            {
                "tenant_id": str(v.tenant_id) if v.tenant_id else None,
                "ok": v.ok,
                "checked": v.checked,
                "reason": v.reason,
                "checked_at": v.checked_at.isoformat(),
            }
            for v in verifications
        ],
        llm_spend_month_usd=float(spend),
        llm_budget_usd=ctx.container.settings.llm_monthly_budget_usd,
    )


@router.get("/audit", response_model=list[AuditEventOut])
async def platform_audit(limit: int = 200, ctx: Ctx = Depends(require_platform)) -> list[object]:
    _need(ctx, P.PLATFORM_AUDIT_READ)
    rows, _ = await AuditRepo(ctx.session).search(None, limit=min(limit, 1000))
    return list(rows)


@router.post("/watchlists/refresh", response_model=Ok)
async def refresh_watchlists(ctx: Ctx = Depends(require_platform)) -> Ok:
    _need(ctx, P.PLATFORM_CONTENT_UPDATE)
    from complymate.ports.queue import QueueName

    await ctx.container.queue.send(QueueName.SCREENING, {"task": "refresh_watchlists", "payload": {}})
    await _platform_audit(ctx, Action.UPDATE, "watchlists", None, after={"refresh": "queued"})
    return Ok()
