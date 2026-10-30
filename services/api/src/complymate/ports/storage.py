from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class StoredObject:
    key: str
    data: bytes
    content_type: str
    metadata: dict[str, str]


class ObjectStorage(Protocol):
    """Bucket-addressed blob storage (S3 / Blob / MinIO). Keys always start with the tenant id."""

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None: ...

    async def get_object(self, bucket: str, key: str) -> StoredObject: ...

    async def delete_object(self, bucket: str, key: str) -> None: ...

    async def presigned_get_url(self, bucket: str, key: str, expires_seconds: int = 300) -> str: ...
