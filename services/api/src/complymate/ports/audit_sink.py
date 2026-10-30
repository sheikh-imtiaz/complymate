from __future__ import annotations

from typing import Any, Protocol


class AuditSink(Protocol):
    """Immutable copy of audit events (S3 Object Lock / Blob immutable storage / local files)."""

    async def write_batch(self, tenant_id: str, batch_key: str, events: list[dict[str, Any]]) -> str: ...
