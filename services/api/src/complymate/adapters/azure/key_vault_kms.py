"""Key Vault keys for envelope encryption: AES data keys wrapped with an RSA-OAEP-256 vault key."""

from __future__ import annotations

import os

from complymate.adapters.azure._credential import async_credential
from complymate.ports.kms import DataKey


class KeyVaultKMS:
    def __init__(self, vault_url: str, key_name: str) -> None:
        self.vault_url = vault_url
        self.key_name = key_name

    async def _crypto(self):  # type: ignore[no-untyped-def]
        from azure.keyvault.keys.aio import KeyClient
        from azure.keyvault.keys.crypto.aio import CryptographyClient

        key = await KeyClient(self.vault_url, async_credential()).get_key(self.key_name)
        return CryptographyClient(key, async_credential())

    async def generate_data_key(self, tenant_id: str) -> DataKey:
        from azure.keyvault.keys.crypto import KeyWrapAlgorithm

        plaintext = os.urandom(32)
        crypto = await self._crypto()
        # Bind to tenant by prefixing the tenant id; checked on unwrap.
        wrapped = await crypto.wrap_key(KeyWrapAlgorithm.rsa_oaep_256, tenant_id.encode()[:36].ljust(36) + plaintext)
        return DataKey(plaintext=plaintext, ciphertext=wrapped.encrypted_key)

    async def decrypt_data_key(self, ciphertext: bytes, tenant_id: str) -> bytes:
        from azure.keyvault.keys.crypto import KeyWrapAlgorithm

        crypto = await self._crypto()
        result = await crypto.unwrap_key(KeyWrapAlgorithm.rsa_oaep_256, ciphertext)
        context, key = result.key[:36], result.key[36:]
        if context.strip() != tenant_id.encode()[:36]:
            raise PermissionError("data key does not belong to this tenant")
        return bytes(key)
