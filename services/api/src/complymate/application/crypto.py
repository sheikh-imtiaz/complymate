"""Per-tenant data keys for documents (envelope encryption, AES-256-GCM). The wrapped key lives in
tenant_settings.encrypted_data_key; KMS / Key Vault unwraps it with the tenant id as encryption context."""

from __future__ import annotations

import os
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.repositories.tenants import TenantRepo
from complymate.ports.kms import KeyManagement

MAGIC = b"CMv1"
_cache: dict[str, bytes] = {}


async def tenant_key(session: AsyncSession, kms: KeyManagement, tenant_id: UUID) -> bytes:
    tid = str(tenant_id)
    settings = await TenantRepo(session).settings(tenant_id)
    if settings.encrypted_data_key is None:
        dk = await kms.generate_data_key(tid)
        settings.encrypted_data_key = dk.ciphertext
        await session.flush()
        _cache[tid] = dk.plaintext
        return dk.plaintext
    cache_key = tid + settings.encrypted_data_key[:16].hex()
    if cache_key not in _cache:
        _cache[cache_key] = await kms.decrypt_data_key(settings.encrypted_data_key, tid)
    return _cache[cache_key]


def encrypt(key: bytes, data: bytes, aad: bytes) -> bytes:
    nonce = os.urandom(12)
    return MAGIC + nonce + AESGCM(key).encrypt(nonce, data, aad)


def decrypt(key: bytes, blob: bytes, aad: bytes) -> bytes:
    if not blob.startswith(MAGIC):
        raise ValueError("not an encrypted ComplyMate document")
    return AESGCM(key).decrypt(blob[4:16], blob[16:], aad)
