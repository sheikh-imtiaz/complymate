from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import SmrCase, SmrNote
from complymate.domain.smr.service import next_reference


class SmrRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.s = session

    async def next_reference(self) -> str:
        year = datetime.now(UTC).year
        count = (await self.s.execute(select(func.count()).where(SmrCase.reference.like(f"SMR-{year}-%")))).scalar_one()
        return next_reference(year, count)

    async def list(self, *, raised_by: UUID | None = None, status: str | None = None) -> Sequence[SmrCase]:
        stmt = select(SmrCase).order_by(SmrCase.created_at.desc())
        if raised_by:
            stmt = stmt.where(SmrCase.raised_by == raised_by)
        if status:
            stmt = stmt.where(SmrCase.status == status)
        return (await self.s.execute(stmt)).scalars().all()

    async def notes(self, case_id: UUID) -> Sequence[SmrNote]:
        stmt = select(SmrNote).where(SmrNote.case_id == case_id).order_by(SmrNote.created_at)
        return (await self.s.execute(stmt)).scalars().all()
