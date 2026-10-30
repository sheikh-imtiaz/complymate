"""Ingests a rule-library source: chunk → embed → store in pgvector."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.agent.rag.chunker import chunk_text
from complymate.db.models import KbSource
from complymate.db.repositories.kb import KbRepo
from complymate.ports.embeddings import EmbeddingProvider


async def ingest_source(
    session: AsyncSession, embeddings: EmbeddingProvider, source: KbSource, text: str, *, force: bool = False
) -> int:
    content_hash = hashlib.sha256(text.encode()).hexdigest()
    if source.content_hash == content_hash and source.chunk_count and not force:
        return source.chunk_count
    chunks = chunk_text(text)
    inputs = [f"{source.title}\n{c.heading or ''}\n{c.content}" for c in chunks]
    vectors: list[list[float]] = []
    for i in range(0, len(inputs), 32):
        vectors.extend(await embeddings.embed(inputs[i : i + 32]))
    await KbRepo(session).replace_chunks(
        source, [(c.heading, c.content, c.tokens, v) for c, v in zip(chunks, vectors, strict=True)]
    )
    source.content_hash = content_hash
    source.indexed_at = datetime.now(UTC)
    source.last_checked_at = source.last_checked_at or datetime.now(UTC)
    await session.flush()
    return len(chunks)
