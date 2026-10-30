from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select

from complymate.api.deps import Ctx, require
from complymate.application import reports as report_service
from complymate.application.exports import download_url
from complymate.db.models import Export, ReportJob, Tenant
from complymate.domain.audit.events import Action
from complymate.domain.billing.limits import has_feature
from complymate.domain.billing.plans import get_plan
from complymate.domain.errors import Forbidden, NotFound, ValidationFailed
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import Scope, scope_for
from complymate.domain.rbac.roles import SMR_ROLES
from complymate.domain.reports.registers import REPORT_TYPES, to_csv, to_xlsx
from complymate.schemas.reports import DownloadOut, ExportOut, ReportJobOut, ScheduleIn

router = APIRouter(tags=["reports"])


@router.get("/reports/dashboard")
async def dashboard(ctx: Ctx = Depends(require(P.REPORT_READ))) -> dict[str, object]:
    return await report_service.dashboard(
        ctx.session,
        include_smr=ctx.principal.role_key in SMR_ROLES,
        user_id=ctx.user_id if ctx.scope is Scope.OWN else None,
    )


@router.get("/reports/types")
async def report_types(ctx: Ctx = Depends(require(P.REPORT_READ))) -> dict[str, str]:
    return REPORT_TYPES


@router.get("/reports/{report_type}")
async def report(
    report_type: str,
    format: str = Query("json", pattern="^(json|csv|xlsx)$"),
    actor_id: str | None = None,
    resource_id: str | None = None,
    action: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    ctx: Ctx = Depends(require(P.REPORT_READ)),
) -> object:
    if report_type not in REPORT_TYPES:
        raise NotFound("unknown report")
    if ctx.scope is not Scope.ALL:
        raise Forbidden("this report needs full report access")
    if report_type == "audit-trail" and scope_for(ctx.principal, P.AUDIT_READ) is None:
        raise Forbidden("missing permission audit:read")
    params = {
        k: v
        for k, v in {
            "actor_id": actor_id,
            "resource_id": resource_id,
            "action": action,
            "date_from": date_from,
            "date_to": date_to,
        }.items()
        if v
    }
    rows, cols = await report_service.rows_for(ctx.session, report_type, params)
    if format == "json":
        return {"columns": cols, "rows": rows[:1000], "total": len(rows)}
    if scope_for(ctx.principal, P.REPORT_EXPORT) is None:
        raise Forbidden("missing permission report:export")
    from complymate.domain.rbac.policy import authorize

    authorize(ctx.principal, P.REPORT_EXPORT, step_up_window_seconds=ctx.container.settings.step_up_mfa_seconds)
    await ctx.record(Action.EXPORT, "report", report_type, after={"format": format, "rows": len(rows), **params})
    if format == "xlsx":
        return Response(
            to_xlsx(rows, REPORT_TYPES[report_type], cols),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{report_type}.xlsx"'},
        )
    return Response(
        to_csv(rows, cols),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{report_type}.csv"'},
    )


@router.post("/reports/regulator-pack", response_model=ReportJobOut, status_code=202)
async def regulator_pack(ctx: Ctx = Depends(require(P.REPORT_EXPORT))) -> object:
    job = ReportJob(
        tenant_id=ctx.tenant_id, report_type="regulator-pack", format="zip", status="queued", requested_by=ctx.user_id
    )
    ctx.session.add(job)
    await ctx.session.flush()
    await ctx.container.workflows.start("regulator_pack", {"tenant_id": str(ctx.tenant_id), "job_id": str(job.id)})
    await ctx.record(Action.EXPORT, "regulator_pack", job.id, after={"status": "queued"})
    return job


@router.get("/reports/jobs/list", response_model=list[ReportJobOut])
async def jobs(ctx: Ctx = Depends(require(P.REPORT_READ))) -> list[object]:
    stmt = select(ReportJob).order_by(ReportJob.created_at.desc()).limit(100)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.post("/reports/schedules", response_model=ReportJobOut, status_code=201)
async def schedule(body: ScheduleIn, ctx: Ctx = Depends(require(P.REPORT_EXPORT))) -> object:
    tenant = await ctx.session.get(Tenant, ctx.tenant_id)
    if not has_feature(get_plan(tenant.plan_code if tenant else "solo"), "scheduled_reports"):
        raise ValidationFailed("scheduled reports are available on the Practice plan")
    if body.report_type not in REPORT_TYPES:
        raise ValidationFailed("unknown report type")
    if len(body.cron.split()) != 5:
        raise ValidationFailed("cron must have 5 fields")
    job = ReportJob(
        tenant_id=ctx.tenant_id,
        report_type=body.report_type,
        format=body.format,
        status="scheduled",
        requested_by=ctx.user_id,
        schedule_cron=body.cron,
        recipients=[str(r) for r in body.recipients],
        params=body.params,
    )
    ctx.session.add(job)
    await ctx.session.flush()
    await ctx.container.scheduler.upsert_schedule(
        f"report-{job.id}",
        body.cron,
        "send_scheduled_reports",
        {"tenant_id": str(ctx.tenant_id), "job_id": str(job.id)},
    )
    await ctx.record(Action.CREATE, "report_schedule", job.id, after={"cron": body.cron, "type": body.report_type})
    return job


@router.delete("/reports/schedules/{job_id}")
async def unschedule(job_id: UUID, ctx: Ctx = Depends(require(P.REPORT_EXPORT))) -> dict[str, bool]:
    job = await ctx.session.get(ReportJob, job_id)
    if job is None or not job.schedule_cron:
        raise NotFound("schedule not found")
    await ctx.container.scheduler.delete_schedule(f"report-{job.id}")
    job.status = "cancelled"
    await ctx.record(Action.DELETE, "report_schedule", job.id)
    return {"ok": True}


@router.get("/exports", response_model=list[ExportOut])
async def exports(ctx: Ctx = Depends(require(P.REPORT_EXPORT))) -> list[object]:
    stmt = select(Export).order_by(Export.created_at.desc()).limit(100)
    return list((await ctx.session.execute(stmt)).scalars().all())


@router.get("/exports/{export_id}/download", response_model=DownloadOut)
async def download(export_id: UUID, ctx: Ctx = Depends(require(P.REPORT_EXPORT))) -> DownloadOut:
    export = await ctx.session.get(Export, export_id)
    if export is None:
        raise NotFound("export not found")
    await ctx.record(Action.EXPORT, "export", export.id, after={"kind": export.kind})
    return DownloadOut(url=await download_url(ctx.container, export), filename=export.filename)
