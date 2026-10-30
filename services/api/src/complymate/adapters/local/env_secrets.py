"""Secrets from environment variables (local). Name `stripe/secret_key` → env STRIPE_SECRET_KEY."""

from __future__ import annotations

import json
import os
from typing import Any


class EnvSecrets:
    @staticmethod
    def _env_name(name: str) -> str:
        return name.replace("/", "_").replace("-", "_").upper()

    async def get_secret(self, name: str) -> str:
        value = os.environ.get(self._env_name(name))
        if value is None:
            raise KeyError(f"secret {name} not set")
        return value

    async def get_json(self, name: str) -> dict[str, Any]:
        result: dict[str, Any] = json.loads(await self.get_secret(name))
        return result
