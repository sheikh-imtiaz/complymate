"""Local KMS: wraps data keys with AES-GCM under a key derived from DEV_JWT_SECRET. Dev only."""

from __future__ import annotations

import hashlib
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from complymate.ports.kms import DataKey


class LocalKMS:
    def __init__(self, master_secret: str) -> None:
        self._master = hashlib.sha256(master_secret.encode()).digest()

    async def generate_data_key(self, tenant_id: str) -> DataKey:
        plaintext = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(12)
        ct = AESGCM(self._master).encrypt(nonce, plaintext, tenant_id.encode())
        return DataKey(plaintext=plaintext, ciphertext=nonce + ct)

    async def decrypt_data_key(self, ciphertext: bytes, tenant_id: str) -> bytes:
        return AESGCM(self._master).decrypt(ciphertext[:12], ciphertext[12:], tenant_id.encode())
