"""Regulator pack: one ZIP with the approved program, registers, risk summary, screening history, training
records, audit trail and an audit-chain verification result."""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select

from complymate.application import reports
from complymate.application.exports import save_export
from complymate.application.notify import notify
from complymate.container import get_container
from complymate.db.models import Program, ProgramVersion, ReportJob, Tenant
from complymate.db.repositories.audit import AuditRepo
from complymate.db.repositories.programs import ProgramRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.domain.audit.hash_chain import verify_chain
from complymate.domain.programs.export import ExportProgram, ExportSection, to_docx
from complymate.domain.reports.registers import to_csv, to_xlsx
from complymate.domain.reports.regulator_pack import build_zip
from complymate.workers._common import system_audit


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    container = get_container()
    async with tenant_session(tenant_id) as session:
        job = await session.get(ReportJob, UUID(payload["job_id"]))
        tenant = await session.get(Tenant, tenant_id)
        assert job is not None and tenant is not None
        job.status = "running"
        await session.flush()
        try:
            files: dict[str, bytes] = {}
            program = (await session.execute(select(Program))).scalar_one_or_none()
            if program and program.approved_version_id:
                version = await session.get(ProgramVersion, program.approved_version_id)
                assert version is not None
                sections = await ProgramRepo(session).sections(version.id)
                files[f"01-program-v{version.version_number}.docx"] = await asyncio.to_thread(
                    to_docx,
                    ExportProgram(
                        tenant.name,
                        version.version_number,
                        version.status,
                        version.approved_at.date().isoformat() if version.approved_at else None,
                        None,
                        [ExportSection(s.title, s.content_html, s.citations) for s in sections],
                    ),
                    f"{container.settings.templates_dir}/program.docx",
                )
            for idx, rtype in enumerate(
                ["client-register", "risk-summary", "screening-history", "program-versions", "training-completion"],
                start=2,
            ):
                rows, cols = await reports.rows_for(session, rtype)
                files[f"{idx:02d}-{rtype}.xlsx"] = to_xlsx(rows, rtype, cols)
            rows, cols = await reports.rows_for(session, "audit-trail")
            files["07-audit-trail.csv"] = to_csv(rows, cols)
            chain = verify_chain([e async for e in AuditRepo(session).iter_chain(tenant_id)])
            files["08-audit-chain-verification.json"] = json.dumps(chain.__dict__, indent=2).encode()
            data = build_zip(files, tenant.name, str(job.requested_by))
            export = await save_export(
                session,
                container,
                tenant_id=tenant_id,
                kind="regulator_pack",
                filename=f"regulator-pack-{datetime.now(UTC):%Y%m%d}.zip",
                content_type="application/zip",
                data=data,
                created_by=job.requested_by,
            )
            job.export_id = export.id
            job.status = "done"
            job.completed_at = datetime.now(UTC)
            if job.requested_by:
                await notify(
                    session,
                    container,
                    tenant_id=tenant_id,
                    user_ids=[job.requested_by],
                    kind="report_ready",
                    title="Your regulator pack is ready",
                    link="/reports",
                )
            await system_audit(
                session,
                tenant_id,
                Action.EXPORT,
                "regulator_pack",
                job.id,
                after={"files": sorted(files), "export_id": str(export.id)},
            )
        except Exception as exc:
            job.status = "failed"
            job.error = type(exc).__name__
            raise
        return {"status": job.status, "export_id": str(job.export_id) if job.export_id else None}
