"""AWS Secrets Manager with a small in-process cache (Lambda containers are reused)."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any

from complymate.adapters.aws._session import client


class SecretsManagerStore:
    def __init__(self, region: str, ttl_seconds: int = 300, endpoint_url: str | None = None) -> None:
        self._client = client("secretsmanager", region, endpoint_url)
        self._cache: dict[str, tuple[float, str]] = {}
        self.ttl = ttl_seconds

    async def get_secret(self, name: str) -> str:
        cached = self._cache.get(name)
        if cached and cached[0] > time.monotonic():
            return cached[1]
        resp = await asyncio.to_thread(self._client.get_secret_value, SecretId=name)
        value: str = resp["SecretString"]
        self._cache[name] = (time.monotonic() + self.ttl, value)
        return value

    async def get_json(self, name: str) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(await self.get_secret(name))
        return result
