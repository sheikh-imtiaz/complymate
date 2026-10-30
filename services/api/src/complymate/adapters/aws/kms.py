"""AWS KMS envelope encryption. Encryption context {"tenant_id": ...} binds keys to a tenant."""

from __future__ import annotations

import asyncio

from complymate.adapters.aws._session import client
from complymate.ports.kms import DataKey


class AwsKMS:
    def __init__(self, region: str, key_id: str, endpoint_url: str | None = None) -> None:
        self.key_id = key_id
        self._client = client("kms", region, endpoint_url)

    async def generate_data_key(self, tenant_id: str) -> DataKey:
        resp = await asyncio.to_thread(
            self._client.generate_data_key,
            KeyId=self.key_id,
            KeySpec="AES_256",
            EncryptionContext={"tenant_id": tenant_id},
        )
        return DataKey(plaintext=resp["Plaintext"], ciphertext=resp["CiphertextBlob"])

    async def decrypt_data_key(self, ciphertext: bytes, tenant_id: str) -> bytes:
        resp = await asyncio.to_thread(
            self._client.decrypt,
            CiphertextBlob=ciphertext,
            EncryptionContext={"tenant_id": tenant_id},
        )
        plaintext: bytes = resp["Plaintext"]
        return plaintext
