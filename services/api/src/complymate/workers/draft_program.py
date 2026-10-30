"""Program drafting workflow steps. On AWS a Step Functions Map state calls `draft_program_section` for each
section (in parallel, with retries) and then `draft_program_finalize`. Locally `run_workflow` does it in order."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from complymate.agent.rag.retriever import Retriever
from complymate.agent.tools.draft_section import draft_section
from complymate.application import llm_usage
from complymate.application.notify import notify
from complymate.container import get_container
from complymate.db.models import Program, ProgramVersion, Tenant
from complymate.db.repositories.programs import ProgramRepo
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.workers._common import system_audit

log = structlog.get_logger(__name__)


async def run_section(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    container = get_container()
    async with tenant_session(tenant_id) as session:
        version = await session.get(ProgramVersion, UUID(payload["version_id"]))
        if version is None or version.locked:
            return {"status": "skipped"}
        version.draft_status = "running"
        program = await session.get(Program, version.program_id)
        tenant = await session.get(Tenant, tenant_id)
        assert program is not None and tenant is not None
        section = await ProgramRepo(session).section(version.id, payload["section"])
        if section is None:
            return {"status": "missing"}
        result = await draft_section(
            container.llm,
            Retriever(session, container.embeddings),
            section_key=section.key,
            answers=program.interview_answers or {},
            jurisdiction=tenant.jurisdiction,
            firm_name=tenant.name,
        )
        # The draft is a suggestion: a person accepts or rejects it (ai-decision endpoint).
        section.ai_draft_html = result.html
        section.citations = result.citations
        section.ai_accepted = None
        await llm_usage.record(
            session,
            container.settings,
            tenant_id=tenant_id,
            purpose="program_drafter",
            model=result.model,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
        )
        await system_audit(
            session,
            tenant_id,
            Action.AI_SUGGESTION,
            "program_section",
            section.id,
            ai={
                "model": result.model,
                "prompt_version": container.settings.prompt_version,
                "sources": [c["title"] for c in result.citations],
                "section": section.key,
            },
        )
        return {"status": "drafted", "section": section.key}


async def finalize(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    async with tenant_session(tenant_id) as session:
        version = await session.get(ProgramVersion, UUID(payload["version_id"]))
        if version is None:
            return {"status": "missing"}
        version.draft_status = payload.get("status", "done")
        if payload.get("requested_by"):
            await notify(
                session,
                get_container(),
                tenant_id=tenant_id,
                user_ids=[UUID(payload["requested_by"])],
                kind="draft_ready",
                title="Your AML/CTF program draft is ready to review",
                link=f"/program/{version.id}",
            )
        return {"status": version.draft_status}


async def run_workflow(payload: dict[str, Any]) -> dict[str, Any]:
    failed = []
    for key in payload["sections"]:
        try:
            await run_section({**payload, "section": key})
        except Exception:
            log.exception("draft.section_failed", section=key)
            failed.append(key)
    return await finalize({**payload, "status": "failed" if len(failed) == len(payload["sections"]) else "done"})
