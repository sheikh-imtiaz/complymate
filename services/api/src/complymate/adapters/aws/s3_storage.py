"""Amazon S3 storage with SSE-KMS. Also used against MinIO locally (custom endpoint, no KMS)."""

from __future__ import annotations

import asyncio
from typing import Any

from complymate.adapters.aws._session import client
from complymate.ports.storage import StoredObject


class S3Storage:
    def __init__(
        self,
        region: str,
        kms_key_id: str | None = None,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        extra: dict[str, Any] = {}
        if access_key and secret_key:
            extra = {"aws_access_key_id": access_key, "aws_secret_access_key": secret_key}
        self._client = client("s3", region, endpoint_url, **extra)
        self.kms_key_id = kms_key_id

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        args: dict[str, Any] = {
            "Bucket": bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type,
            "Metadata": metadata or {},
        }
        if self.kms_key_id:
            args["ServerSideEncryption"] = "aws:kms"
            args["SSEKMSKeyId"] = self.kms_key_id
            args["BucketKeyEnabled"] = True
        await asyncio.to_thread(self._client.put_object, **args)

    async def get_object(self, bucket: str, key: str) -> StoredObject:
        resp = await asyncio.to_thread(self._client.get_object, Bucket=bucket, Key=key)
        data = await asyncio.to_thread(resp["Body"].read)
        return StoredObject(
            key=key,
            data=data,
            content_type=resp.get("ContentType", "application/octet-stream"),
            metadata=resp.get("Metadata", {}),
        )

    async def delete_object(self, bucket: str, key: str) -> None:
        await asyncio.to_thread(self._client.delete_object, Bucket=bucket, Key=key)

    async def presigned_get_url(self, bucket: str, key: str, expires_seconds: int = 300) -> str:
        url: str = await asyncio.to_thread(
            self._client.generate_presigned_url,
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
        return url
