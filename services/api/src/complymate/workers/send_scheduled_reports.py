"""Scheduled reports by email (Practice plan)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from complymate.application import reports
from complymate.container import get_container
from complymate.db.models import ReportJob, Tenant
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.domain.reports.registers import REPORT_TYPES, to_csv, to_xlsx
from complymate.ports.email import Attachment
from complymate.workers._common import render, system_audit


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    container = get_container()
    async with tenant_session(tenant_id) as session:
        job = await session.get(ReportJob, UUID(payload["job_id"]))
        tenant = await session.get(Tenant, tenant_id)
        if job is None or tenant is None or job.status == "cancelled" or not job.recipients:
            return {"status": "skipped"}
        rows, cols = await reports.rows_for(session, job.report_type, job.params)
        title = REPORT_TYPES[job.report_type]
        if job.format == "xlsx":
            att = Attachment(
                f"{job.report_type}.xlsx",
                to_xlsx(rows, title, cols),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            att = Attachment(f"{job.report_type}.csv", to_csv(rows, cols), "text/csv")
        html = render(
            "emails/report_ready.html",
            firm=tenant.name,
            report=title,
            rows=len(rows),
            generated=datetime.now(UTC).strftime("%d %b %Y %H:%M UTC"),
        )
        await container.email.send(list(job.recipients), f"{tenant.name}: {title}", html, attachments=[att])
        job.completed_at = datetime.now(UTC)
        await system_audit(
            session,
            tenant_id,
            Action.EXPORT,
            "scheduled_report",
            job.id,
            after={"recipients": len(job.recipients), "rows": len(rows)},
        )
    return {"status": "sent"}
