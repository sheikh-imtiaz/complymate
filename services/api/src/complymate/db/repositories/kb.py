from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import KbChunk, KbSource


@dataclass
class RetrievedChunk:
    chunk_id: UUID
    source_id: UUID
    title: str
    url: str | None
    publisher: str
    heading: str | None
    content: str
    last_checked_at: datetime | None
    score: float


class KbRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def search(self, embedding: list[float], jurisdiction: str, k: int = 6) -> list[RetrievedChunk]:
        distance = KbChunk.embedding.cosine_distance(embedding)
        stmt = (
            select(KbChunk, KbSource, distance.label("distance"))
            .join(KbSource, KbSource.id == KbChunk.source_id)
            .where(KbSource.status == "active", KbSource.jurisdiction == jurisdiction)
            .order_by(distance)
            .limit(k)
        )
        out = []
        for chunk, source, dist in (await self.s.execute(stmt)).all():
            out.append(
                RetrievedChunk(
                    chunk.id,
                    source.id,
                    source.title,
                    source.url,
                    source.publisher,
                    chunk.heading,
                    chunk.content,
                    source.last_checked_at,
                    round(1 - float(dist), 4),
                )
            )
        return out

    async def replace_chunks(self, source: KbSource, chunks: list[tuple[str | None, str, int, list[float]]]) -> None:
        await self.s.execute(delete(KbChunk).where(KbChunk.source_id == source.id))
        for i, (heading, content, tokens, emb) in enumerate(chunks):
            self.s.add(
                KbChunk(
                    source_id=source.id, chunk_index=i, heading=heading, content=content, tokens=tokens, embedding=emb
                )
            )
        source.chunk_count = len(chunks)
        await self.s.flush()

    async def sources(self, jurisdiction: str | None = None) -> list[KbSource]:
        stmt = select(KbSource).order_by(KbSource.jurisdiction, KbSource.title)
        if jurisdiction:
            stmt = stmt.where(KbSource.jurisdiction == jurisdiction)
        return list((await self.s.execute(stmt)).scalars().all())
