"""Vector search over the rule library (pgvector cosine)."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.repositories.kb import KbRepo, RetrievedChunk
from complymate.ports.embeddings import EmbeddingProvider

MIN_SCORE = 0.05


class Retriever:
    def __init__(self, session: AsyncSession, embeddings: EmbeddingProvider) -> None:
        self.repo = KbRepo(session)
        self.embeddings = embeddings

    async def search(self, query: str, jurisdiction: str, k: int = 6) -> list[RetrievedChunk]:
        [vector] = await self.embeddings.embed([query])
        results = await self.repo.search(vector, jurisdiction, k)
        return [r for r in results if r.score >= MIN_SCORE]


def format_sources(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for i, c in enumerate(chunks, start=1):
        checked = c.last_checked_at.date().isoformat() if c.last_checked_at else "unknown"
        blocks.append(
            f"[S{i}] {c.title}{' — ' + c.heading if c.heading else ''} ({c.publisher}, last checked {checked})\n{c.content}"
        )
    return "\n\n".join(blocks)


def citations(chunks: list[RetrievedChunk]) -> list[dict[str, object]]:
    return [
        {
            "ref": f"S{i}",
            "title": c.title,
            "url": c.url,
            "publisher": c.publisher,
            "heading": c.heading,
            "last_checked_at": c.last_checked_at.isoformat() if c.last_checked_at else None,
            "score": c.score,
            "source_id": str(c.source_id),
            "chunk_id": str(c.chunk_id),
        }
        for i, c in enumerate(chunks, start=1)
    ]
