from __future__ import annotations

from functools import lru_cache
from typing import Any


@lru_cache(maxsize=1)
def async_credential() -> Any:
    """Managed identity in Container Apps; developer credentials locally."""
    from azure.identity.aio import DefaultAzureCredential

    return DefaultAzureCredential()


@lru_cache(maxsize=1)
def sync_credential() -> Any:
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()
