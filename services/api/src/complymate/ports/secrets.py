from __future__ import annotations

from typing import Any, Protocol


class SecretStore(Protocol):
    async def get_secret(self, name: str) -> str: ...

    async def get_json(self, name: str) -> dict[str, Any]: ...
