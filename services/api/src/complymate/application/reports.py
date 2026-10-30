"""Report rows and the compliance dashboard (shared by API and scheduled-report workers)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import (
    AuditEventRow,
    Client,
    Program,
    ProgramVersion,
    QuizAttempt,
    RiskAssessment,
    ScreeningMatch,
    ScreeningRun,
    SmrCase,
    Task,
    TrainingAssignment,
    TrainingModule,
    User,
)
from complymate.domain.reports.dashboard import DashboardData
from complymate.domain.reports.registers import REPORT_TYPES


async def dashboard(session: AsyncSession, *, include_smr: bool, user_id: UUID | None = None) -> dict[str, Any]:
    d = DashboardData()
    owner_filter = [] if user_id is None else [(Client.created_by == user_id) | (Client.assigned_to == user_id)]
    rows = await session.execute(
        select(Client.risk_level, func.count())
        .where(Client.status.in_(("pending", "approved")), *owner_filter)
        .group_by(Client.risk_level)
    )
    d.clients_by_risk = {(lvl or "unassessed"): n for lvl, n in rows.all()}
    rows = await session.execute(select(Client.status, func.count()).where(*owner_filter).group_by(Client.status))
    d.clients_by_status = {str(k): int(v) for k, v in rows.all()}
    d.overdue_reviews = (
        await session.execute(
            select(func.count()).where(
                Client.status == "approved", Client.next_review_date < date.today(), *owner_filter
            )
        )
    ).scalar_one()
    d.open_matches = (
        await session.execute(select(func.count()).where(ScreeningMatch.status.in_(("open", "needs_info"))))
    ).scalar_one()
    task_filter = [] if user_id is None else [Task.assignee_id == user_id]
    d.open_tasks = (await session.execute(select(func.count()).where(Task.status == "open", *task_filter))).scalar_one()
    d.overdue_tasks = (
        await session.execute(
            select(func.count()).where(Task.status == "open", Task.due_date < date.today(), *task_filter)
        )
    ).scalar_one()
    ta_filter = [] if user_id is None else [TrainingAssignment.user_id == user_id]
    d.training_total = (
        await session.execute(select(func.count()).select_from(TrainingAssignment).where(*ta_filter))
    ).scalar_one()
    d.training_completed = (
        await session.execute(select(func.count()).where(TrainingAssignment.completed_at.is_not(None), *ta_filter))
    ).scalar_one()
    d.training_overdue = (
        await session.execute(
            select(func.count()).where(
                TrainingAssignment.completed_at.is_(None), TrainingAssignment.due_date < date.today(), *ta_filter
            )
        )
    ).scalar_one()
    program = (await session.execute(select(Program))).scalar_one_or_none()
    d.program_status = program.status if program else None
    d.program_next_review = program.next_review_due.isoformat() if program and program.next_review_due else None
    if include_smr:
        d.open_smrs = (
            await session.execute(
                select(func.count()).where(SmrCase.status.in_(("draft", "under_review", "decided_report")))
            )
        ).scalar_one()
    return d.as_dict()


async def rows_for(
    session: AsyncSession, report_type: str, params: dict[str, Any] | None = None
) -> tuple[list[dict[str, Any]], list[str]]:
    params = params or {}
    if report_type not in REPORT_TYPES:
        raise KeyError(report_type)
    if report_type == "client-register":
        cols = [
            "display_name",
            "client_type",
            "status",
            "risk_level",
            "risk_score",
            "is_pep",
            "next_review_date",
            "last_screened_at",
            "created_at",
            "approved_at",
        ]
        clients = (await session.execute(select(Client).order_by(Client.display_name))).scalars().all()
        return [{c: getattr(r, c) for c in cols} for r in clients], cols
    if report_type == "risk-summary":
        cols = ["client", "level", "score", "override_level", "rules_version", "status", "reasons", "created_at"]
        rows = (
            await session.execute(
                select(RiskAssessment, Client.display_name)
                .join(Client, Client.id == RiskAssessment.client_id)
                .where(RiskAssessment.status != "superseded")
                .order_by(RiskAssessment.created_at.desc())
            )
        ).all()
        return [
            {
                "client": name,
                "level": a.level,
                "score": a.score,
                "override_level": a.override_level,
                "rules_version": a.rules_version,
                "status": a.status,
                "reasons": "; ".join(r["description"] for r in a.reasons),
                "created_at": a.created_at,
            }
            for a, name in rows
        ], cols
    if report_type == "screening-history":
        cols = ["client", "trigger", "match_count", "screened_names", "created_at"]
        runs = (
            await session.execute(
                select(ScreeningRun, Client.display_name)
                .join(Client, Client.id == ScreeningRun.client_id)
                .order_by(ScreeningRun.created_at.desc())
                .limit(10_000)
            )
        ).all()
        return [
            {
                "client": name,
                "trigger": r.trigger,
                "match_count": r.match_count,
                "screened_names": len(r.screened_names),
                "created_at": r.created_at,
            }
            for r, name in runs
        ], cols
    if report_type == "program-versions":
        cols = ["version_number", "status", "change_summary", "submitted_at", "approved_at", "locked"]
        versions = (
            (await session.execute(select(ProgramVersion).order_by(ProgramVersion.version_number))).scalars().all()
        )
        return [{c: getattr(v, c) for c in cols} for v in versions], cols
    if report_type == "training-completion":
        cols = ["user", "module", "due_date", "completed_at", "best_score"]
        assigned = (
            await session.execute(
                select(TrainingAssignment, User.email, TrainingModule.title)
                .join(User, User.id == TrainingAssignment.user_id)
                .join(TrainingModule, TrainingModule.id == TrainingAssignment.module_id)
            )
        ).all()
        scores: dict[tuple[UUID, UUID], float] = {}
        for att in (await session.execute(select(QuizAttempt))).scalars().all():
            key = (att.user_id, att.module_id)
            scores[key] = max(scores.get(key, 0.0), float(att.score))
        return [
            {
                "user": email,
                "module": title,
                "due_date": a.due_date,
                "completed_at": a.completed_at,
                "best_score": scores.get((a.user_id, a.module_id)),
            }
            for a, email, title in assigned
        ], cols
    # audit-trail
    cols = ["occurred_at", "actor_id", "actor_role", "action", "resource_type", "resource_id", "reason", "hash"]
    stmt = select(AuditEventRow).order_by(AuditEventRow.seq)
    if params.get("actor_id"):
        stmt = stmt.where(AuditEventRow.actor_id == UUID(params["actor_id"]))
    if params.get("resource_id"):
        stmt = stmt.where(AuditEventRow.resource_id == params["resource_id"])
    if params.get("action"):
        stmt = stmt.where(AuditEventRow.action == params["action"])
    if params.get("date_from"):
        stmt = stmt.where(AuditEventRow.occurred_at >= datetime.fromisoformat(params["date_from"]))
    if params.get("date_to"):
        stmt = stmt.where(AuditEventRow.occurred_at <= datetime.fromisoformat(params["date_to"]))
    events = (await session.execute(stmt.limit(100_000))).scalars().all()
    return [{c: getattr(e, c) for c in cols} for e in events], cols
