from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class DataKey:
    plaintext: bytes
    ciphertext: bytes


class KeyManagement(Protocol):
    """Envelope encryption. The encryption context binds every data key to a tenant."""

    async def generate_data_key(self, tenant_id: str) -> DataKey: ...

    async def decrypt_data_key(self, ciphertext: bytes, tenant_id: str) -> bytes: ...
