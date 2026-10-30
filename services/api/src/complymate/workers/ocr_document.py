"""OCR worker: decrypts the document, extracts identity fields (Textract / Document Intelligence), stores them
for staff to confirm. The AI never confirms — a person does (documents router)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

import structlog

from complymate.application.documents import load_document
from complymate.container import get_container
from complymate.db.models import ClientDocument
from complymate.db.session import tenant_session
from complymate.domain.audit.events import Action
from complymate.workers._common import system_audit

log = structlog.get_logger(__name__)


async def run(payload: dict[str, Any]) -> dict[str, Any]:
    tenant_id = UUID(payload["tenant_id"])
    container = get_container()
    async with tenant_session(tenant_id) as session:
        doc = await session.get(ClientDocument, UUID(payload["document_id"]))
        if doc is None:
            return {"status": "missing"}
        doc.ocr_status = "processing"
        await session.flush()
        try:
            data = await load_document(session, container, doc)
            result = await container.ocr.extract_identity(data, doc.content_type)
            doc.ocr_fields = result.fields
            doc.ocr_confidence = result.confidence
            doc.ocr_status = "done"
        except Exception as exc:
            log.warning("ocr.failed", error=type(exc).__name__)
            doc.ocr_status = "failed"
        await system_audit(
            session,
            tenant_id,
            Action.AI_SUGGESTION,
            "client_document",
            doc.id,
            ai={
                "source": "ocr",
                "provider": container.settings.cloud_provider,
                "fields": sorted(doc.ocr_fields or {}),
                "status": doc.ocr_status,
            },
        )
        return {"status": doc.ocr_status}
