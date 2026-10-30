"""Azure Blob Storage. Buckets map to containers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from complymate.adapters.azure._credential import async_credential
from complymate.ports.storage import StoredObject


class BlobStorage:
    def __init__(self, account_url: str) -> None:
        from azure.storage.blob.aio import BlobServiceClient

        self.account_url = account_url
        self._service = BlobServiceClient(account_url, credential=async_credential())

    async def put_object(
        self,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> None:
        from azure.storage.blob import ContentSettings

        blob = self._service.get_blob_client(bucket, key)
        await blob.upload_blob(
            data, overwrite=True, metadata=metadata or {}, content_settings=ContentSettings(content_type=content_type)
        )

    async def get_object(self, bucket: str, key: str) -> StoredObject:
        blob = self._service.get_blob_client(bucket, key)
        downloader = await blob.download_blob()
        props = await blob.get_blob_properties()
        return StoredObject(
            key=key,
            data=await downloader.readall(),
            content_type=props.content_settings.content_type or "application/octet-stream",
            metadata=dict(props.metadata or {}),
        )

    async def delete_object(self, bucket: str, key: str) -> None:
        await self._service.get_blob_client(bucket, key).delete_blob()

    async def presigned_get_url(self, bucket: str, key: str, expires_seconds: int = 300) -> str:
        from azure.storage.blob import BlobSasPermissions, generate_blob_sas

        start = datetime.now(UTC) - timedelta(minutes=1)
        expiry = datetime.now(UTC) + timedelta(seconds=expires_seconds)
        delegation_key = await self._service.get_user_delegation_key(start, expiry)
        sas = generate_blob_sas(
            account_name=self._service.account_name,
            container_name=bucket,
            blob_name=key,
            user_delegation_key=delegation_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
            start=start,
        )
        return f"{self.account_url}/{bucket}/{key}?{sas}"
