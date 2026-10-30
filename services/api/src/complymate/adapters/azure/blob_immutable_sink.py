"""Immutable audit copy in Blob Storage with a time-based immutability policy (7 years, locked)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

from complymate.adapters.azure._credential import async_credential


class BlobImmutableSink:
    def __init__(self, account_url: str, container: str, retention_years: int = 7) -> None:
        from azure.storage.blob.aio import BlobServiceClient

        self.container = container
        self.retention = timedelta(days=365 * retention_years + 2)
        self._service = BlobServiceClient(account_url, credential=async_credential())

    async def write_batch(self, tenant_id: str, batch_key: str, events: list[dict[str, Any]]) -> str:
        from azure.storage.blob import ImmutabilityPolicy

        body = "\n".join(json.dumps(e, default=str, sort_keys=True) for e in events).encode()
        name = f"{tenant_id}/{batch_key}.jsonl"
        blob = self._service.get_blob_client(self.container, name)
        await blob.upload_blob(
            body,
            overwrite=False,
            immutability_policy=ImmutabilityPolicy(
                expiry_time=datetime.now(UTC) + self.retention, policy_mode="Locked"
            ),
        )
        return f"{self.container}/{name}"
