from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import ScreeningMatch, ScreeningRun, WatchlistEntryRow, WatchlistVersion
from complymate.domain.screening.service import Candidate
from complymate.domain.screening.watchlist_parser import WatchlistEntry


class ScreeningRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def current_versions(self) -> Sequence[WatchlistVersion]:
        return (await self.s.execute(select(WatchlistVersion).where(WatchlistVersion.is_current))).scalars().all()

    async def candidates_for(self, normalized_name: str, limit: int = 50) -> list[Candidate]:
        """Trigram prefilter in PostgreSQL; precise scoring happens in the domain matcher."""
        await self.s.execute(text("SELECT set_limit(0.25)"))
        stmt = (
            select(WatchlistEntryRow)
            .join(WatchlistVersion, WatchlistVersion.id == WatchlistEntryRow.version_id)
            .where(WatchlistVersion.is_current, WatchlistEntryRow.search_text.op("%")(normalized_name))
            .order_by(func.similarity(WatchlistEntryRow.search_text, normalized_name).desc())
            .limit(limit)
        )
        rows = (await self.s.execute(stmt)).scalars().all()
        return [
            Candidate(r.id, r.source, r.primary_name, [r.primary_name, *r.aliases], r.entity_type, r.dob) for r in rows
        ]

    async def replace_watchlist(
        self, source: str, label: str, checksum: str, entries: list[WatchlistEntry]
    ) -> WatchlistVersion | None:
        existing = (
            await self.s.execute(
                select(WatchlistVersion).where(WatchlistVersion.source == source, WatchlistVersion.is_current)
            )
        ).scalar_one_or_none()
        if existing and existing.checksum == checksum:
            return None  # unchanged
        version = WatchlistVersion(source=source, version_label=label, checksum=checksum, entry_count=len(entries))
        self.s.add(version)
        await self.s.flush()
        for e in entries:
            self.s.add(
                WatchlistEntryRow(
                    version_id=version.id,
                    source=e.source,
                    reference=e.reference,
                    entity_type=e.entity_type,
                    primary_name=e.primary_name,
                    aliases=e.aliases,
                    normalized_names=e.normalized_names,
                    search_text=" | ".join(e.normalized_names),
                    dob=e.dob,
                    nationality=e.nationality,
                    program=e.program,
                )
            )
        await self.s.flush()
        await self.s.execute(
            update(WatchlistVersion)
            .where(WatchlistVersion.source == source, WatchlistVersion.id != version.id)
            .values(is_current=False)
        )
        version.is_current = True
        await self.s.flush()
        return version

    async def runs(self, client_id: UUID) -> Sequence[ScreeningRun]:
        stmt = select(ScreeningRun).where(ScreeningRun.client_id == client_id).order_by(ScreeningRun.created_at.desc())
        return (await self.s.execute(stmt)).scalars().all()

    async def matches(
        self, *, client_id: UUID | None = None, status: str | None = None, limit: int = 200
    ) -> list[dict]:  # type: ignore[type-arg]
        stmt = select(ScreeningMatch, WatchlistEntryRow).join(
            WatchlistEntryRow, WatchlistEntryRow.id == ScreeningMatch.entry_id
        )
        if client_id:
            stmt = stmt.where(ScreeningMatch.client_id == client_id)
        if status:
            stmt = stmt.where(ScreeningMatch.status == status)
        rows = (await self.s.execute(stmt.order_by(ScreeningMatch.created_at.desc()).limit(limit))).all()
        return [
            {
                **m.to_dict(),
                "entry": {
                    "source": e.source,
                    "reference": e.reference,
                    "primary_name": e.primary_name,
                    "aliases": e.aliases,
                    "dob": e.dob,
                    "nationality": e.nationality,
                    "program": e.program,
                    "entity_type": e.entity_type,
                },
            }
            for m, e in rows
        ]

    async def existing_decision(self, client_id: UUID, entry_id: UUID, subject: str) -> str | None:
        """Re-screening keeps earlier false-positive decisions for the same name/entry pair."""
        stmt = (
            select(ScreeningMatch.status)
            .where(
                ScreeningMatch.client_id == client_id,
                ScreeningMatch.entry_id == entry_id,
                ScreeningMatch.subject_name == subject,
                ScreeningMatch.status.in_(("false_positive", "true_match")),
            )
            .order_by(ScreeningMatch.created_at.desc())
            .limit(1)
        )
        return (await self.s.execute(stmt)).scalar_one_or_none()
