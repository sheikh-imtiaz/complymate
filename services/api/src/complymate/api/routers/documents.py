from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import Response

from complymate.api.access import load_client
from complymate.api.deps import Ctx, require
from complymate.application.documents import load_document, mask_fields, store_document
from complymate.application.usage import meter
from complymate.db.models import Client, ClientDocument
from complymate.db.repositories.clients import ClientRepo
from complymate.domain.audit.events import Action
from complymate.domain.errors import Forbidden, NotFound
from complymate.domain.rbac.permissions import P
from complymate.domain.rbac.policy import Scope, check_record_access, scope_for
from complymate.ports.queue import QueueName
from complymate.schemas.documents import ConfirmFieldsIn, DocumentOut

router = APIRouter(tags=["documents"])


@router.post("/clients/{client_id}/documents", response_model=DocumentOut, status_code=201)
async def upload(
    client_id: UUID,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    party_id: UUID | None = Form(None),
    ctx: Ctx = Depends(require(P.DOCUMENT_CREATE)),
) -> object:
    # Staff can upload to clients they own; scope comes from client:update.
    ctx.scope = scope_for(ctx.principal, P.CLIENT_UPDATE) or scope_for(ctx.principal, P.CLIENT_READ) or Scope.OWN
    await load_client(ctx, client_id)
    await meter(ctx.session, ctx.tenant_id, "documents")
    data = await file.read()
    doc = await store_document(
        ctx.session,
        ctx.container,
        tenant_id=ctx.tenant_id,
        client_id=client_id,
        party_id=party_id,
        doc_type=doc_type,
        filename=file.filename or "document",
        content_type=file.content_type or "application/octet-stream",
        data=data,
        uploaded_by=ctx.user_id,
    )
    await ctx.container.queue.send(
        QueueName.OCR,
        {"task": "ocr_document", "payload": {"tenant_id": str(ctx.tenant_id), "document_id": str(doc.id)}},
    )
    await ctx.record(
        Action.CREATE,
        "client_document",
        doc.id,
        after={"client_id": str(client_id), "doc_type": doc_type, "sha256": doc.sha256},
    )
    return doc


def _document_scope(ctx: Ctx) -> tuple[Scope, bool]:
    if (s := scope_for(ctx.principal, P.DOCUMENT_READ)) is not None:
        return s, False
    if scope_for(ctx.principal, P.DOCUMENT_READ_MASKED) is not None:
        return Scope.ALL, True
    raise Forbidden("missing permission document:read")


@router.get("/clients/{client_id}/documents", response_model=list[DocumentOut])
async def list_documents(client_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> list[DocumentOut]:
    scope, masked = _document_scope(ctx)
    client = await load_client(ctx, client_id)
    check_record_access(scope, ctx.principal, owner_ids={client.created_by, client.assigned_to})
    docs = await ClientRepo(ctx.session).documents(client_id)
    out = [DocumentOut.model_validate(d) for d in docs]
    if masked:
        for d in out:
            d.ocr_fields = mask_fields(d.ocr_fields)
    return out


async def _doc(ctx: Ctx, document_id: UUID) -> tuple[ClientDocument, Client]:
    doc = await ctx.session.get(ClientDocument, document_id)
    if doc is None:
        raise NotFound("document not found")
    client = await ctx.session.get(Client, doc.client_id)
    assert client is not None
    return doc, client


@router.get("/documents/{document_id}/download")
async def download(document_id: UUID, ctx: Ctx = Depends(require(P.CLIENT_READ))) -> Response:
    scope, masked = _document_scope(ctx)
    if masked:
        raise Forbidden("auditors see masked document details only")
    doc, client = await _doc(ctx, document_id)
    check_record_access(scope, ctx.principal, owner_ids={client.created_by, client.assigned_to, doc.uploaded_by})
    data = await load_document(ctx.session, ctx.container, doc)
    await ctx.record(Action.VIEW_SENSITIVE, "client_document", doc.id, after={"doc_type": doc.doc_type})
    return Response(
        data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"', "Cache-Control": "no-store"},
    )


@router.post("/documents/{document_id}/confirm", response_model=DocumentOut)
async def confirm_fields(
    document_id: UUID, body: ConfirmFieldsIn, ctx: Ctx = Depends(require(P.CLIENT_UPDATE))
) -> object:
    """Staff confirm (and correct) OCR-extracted fields; optionally copy them onto the client record."""
    from datetime import date

    doc, client = await _doc(ctx, document_id)
    check_record_access(ctx.scope, ctx.principal, owner_ids={client.created_by, client.assigned_to})
    doc.ocr_fields = body.fields
    doc.ocr_confirmed = True
    doc.confirmed_by = ctx.user_id
    if body.apply_to_client and client.client_type == "individual":
        f = body.fields
        if f.get("given_names"):
            client.given_names = f["given_names"]
        if f.get("family_name"):
            client.family_name = f["family_name"]
        if f.get("date_of_birth"):
            try:
                client.date_of_birth = date.fromisoformat(f["date_of_birth"])
            except ValueError:
                pass
        if client.given_names or client.family_name:
            client.display_name = " ".join(x for x in (client.given_names, client.family_name) if x)
    await ctx.record(
        Action.AI_ACCEPTED,
        "client_document",
        doc.id,
        after={"fields_confirmed": sorted(body.fields)},
        ai={"source": "ocr", "decision": "confirmed"},
    )
    return doc
