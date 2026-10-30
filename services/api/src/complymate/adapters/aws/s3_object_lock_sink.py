"""Immutable audit copy in S3 Object Lock (compliance mode, 7 years)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from complymate.adapters.aws._session import client


class S3ObjectLockSink:
    def __init__(self, region: str, bucket: str, retention_years: int = 7, kms_key_id: str | None = None) -> None:
        self.bucket = bucket
        self.retention = timedelta(days=365 * retention_years + 2)
        self.kms_key_id = kms_key_id
        self._client = client("s3", region)

    async def write_batch(self, tenant_id: str, batch_key: str, events: list[dict[str, Any]]) -> str:
        body = "\n".join(json.dumps(e, default=str, sort_keys=True) for e in events).encode()
        key = f"{tenant_id}/{batch_key}.jsonl"
        args: dict[str, Any] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": body,
            "ContentType": "application/x-ndjson",
            "ObjectLockMode": "COMPLIANCE",
            "ObjectLockRetainUntilDate": datetime.now(UTC) + self.retention,
            "ChecksumSHA256": base64.b64encode(hashlib.sha256(body).digest()).decode(),
        }
        if self.kms_key_id:
            args["ServerSideEncryption"] = "aws:kms"
            args["SSEKMSKeyId"] = self.kms_key_id
        await asyncio.to_thread(self._client.put_object, **args)
        return f"s3://{self.bucket}/{key}"
