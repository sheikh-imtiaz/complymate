from __future__ import annotations

import hashlib
import uuid
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.application.crypto import decrypt, encrypt, tenant_key
from complymate.container import Container
from complymate.db.models import ClientDocument
from complymate.domain.errors import ValidationFailed

ALLOWED_TYPES = {"image/jpeg", "image/png", "application/pdf", "text/plain"}
DOC_TYPES = {
    "passport",
    "drivers_licence",
    "birth_certificate",
    "medicare_card",
    "national_id",
    "proof_of_address",
    "asic_extract",
    "companies_office_extract",
    "certificate_of_registration",
    "trust_deed",
    "partnership_agreement",
    "source_of_funds",
    "other",
    "nz_firearms_licence",
}


def _sniff(data: bytes, declared: str) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG"):
        return "image/png"
    return declared


async def store_document(
    session: AsyncSession,
    container: Container,
    *,
    tenant_id: UUID,
    client_id: UUID,
    party_id: UUID | None,
    doc_type: str,
    filename: str,
    content_type: str,
    data: bytes,
    uploaded_by: UUID,
) -> ClientDocument:
    if doc_type not in DOC_TYPES:
        raise ValidationFailed(f"unknown document type {doc_type}")
    if len(data) > container.settings.max_upload_bytes:
        raise ValidationFailed("file is larger than 5 MB")
    actual = _sniff(data, content_type)
    if actual not in ALLOWED_TYPES:
        raise ValidationFailed("upload a JPEG, PNG or PDF")
    doc_id = uuid.uuid4()
    key = f"{tenant_id}/clients/{client_id}/documents/{doc_id}"
    dek = await tenant_key(session, container.kms, tenant_id)
    blob = encrypt(dek, data, aad=key.encode())
    await container.storage.put_object(
        container.settings.documents_bucket,
        key,
        blob,
        "application/octet-stream",
        {"tenant-id": str(tenant_id), "encrypted": "aes-gcm"},
    )
    doc = ClientDocument(
        id=doc_id,
        tenant_id=tenant_id,
        client_id=client_id,
        party_id=party_id,
        doc_type=doc_type,
        storage_key=key,
        filename=filename[:255],
        content_type=actual,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
        encrypted=True,
        ocr_status="pending",
        uploaded_by=uploaded_by,
    )
    session.add(doc)
    await session.flush()
    return doc


async def load_document(session: AsyncSession, container: Container, doc: ClientDocument) -> bytes:
    stored = await container.storage.get_object(container.settings.documents_bucket, doc.storage_key)
    if not doc.encrypted:
        return stored.data
    dek = await tenant_key(session, container.kms, doc.tenant_id)
    return decrypt(dek, stored.data, aad=doc.storage_key.encode())


def mask_fields(fields: dict[str, str]) -> dict[str, str]:
    """Auditor view: show the shape of values, not the values."""
    out = {}
    for k, v in fields.items():
        s = str(v)
        out[k] = (s[:1] + "•" * max(0, len(s) - 2) + s[-1:]) if len(s) > 2 else "••"
    return out
