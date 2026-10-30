"""Azure Key Vault secrets. Secret names use dashes (`stripe/secret_key` → `stripe-secret-key`)."""

from __future__ import annotations

import json
from typing import Any

from complymate.adapters.azure._credential import async_credential


class KeyVaultSecrets:
    def __init__(self, vault_url: str) -> None:
        from azure.keyvault.secrets.aio import SecretClient

        self._client = SecretClient(vault_url, async_credential())
        self._cache: dict[str, str] = {}

    async def get_secret(self, name: str) -> str:
        kv_name = name.replace("/", "-").replace("_", "-")
        if kv_name not in self._cache:
            secret = await self._client.get_secret(kv_name)
            self._cache[kv_name] = secret.value or ""
        return self._cache[kv_name]

    async def get_json(self, name: str) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(await self.get_secret(name))
        return result
