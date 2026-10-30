from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.container import Container
from complymate.db.models import Export
from complymate.domain.programs.export import safe_filename


async def save_export(
    session: AsyncSession,
    container: Container,
    *,
    tenant_id: UUID,
    kind: str,
    filename: str,
    content_type: str,
    data: bytes,
    created_by: UUID | None,
) -> Export:
    export_id = uuid.uuid4()
    name = safe_filename(filename)
    key = f"{tenant_id}/exports/{export_id}/{name}"
    await container.storage.put_object(
        container.settings.exports_bucket, key, data, content_type, {"tenant-id": str(tenant_id)}
    )
    export = Export(
        id=export_id,
        tenant_id=tenant_id,
        kind=kind,
        storage_key=key,
        filename=name,
        content_type=content_type,
        size_bytes=len(data),
        created_by=created_by,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    session.add(export)
    await session.flush()
    return export


async def download_url(container: Container, export: Export) -> str:
    return await container.storage.presigned_get_url(container.settings.exports_bucket, export.storage_key, 300)
