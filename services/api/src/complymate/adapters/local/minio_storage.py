"""S3-compatible storage for MinIO (local). Reuses the S3 adapter with a custom endpoint."""

from __future__ import annotations

from complymate.adapters.aws.s3_storage import S3Storage


class MinioStorage(S3Storage):
    def __init__(self, endpoint_url: str, access_key: str, secret_key: str, region: str = "us-east-1") -> None:
        super().__init__(
            region=region,
            endpoint_url=endpoint_url,
            access_key=access_key,
            secret_key=secret_key,
            kms_key_id=None,
        )
