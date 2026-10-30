"""Tool: check a name against current sanctions lists (read-only; does not create a screening record)."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.repositories.screening import ScreeningRepo
from complymate.domain.screening.service import ScreenSubject, screen


async def check_sanctions(session: AsyncSession, name: str, entity: bool = False) -> list[dict[str, Any]]:
    outcome = await screen([ScreenSubject(name, entity)], ScreeningRepo(session))
    return [
        {"matched_name": m.matched_name, "source": m.candidate.source, "score": m.score, "method": m.method}
        for m in outcome.matches[:5]
    ]


def make_tool(session: AsyncSession) -> Any:
    from strands import tool

    @tool
    async def check_sanctions_list(name: str, is_entity: bool = False) -> list[dict[str, Any]]:
        """Check whether a name is similar to an entry on the current sanctions lists (DFAT / NZ).
        This is a preliminary check only; formal screening must be run on the client record.

        Args:
            name: Person or organisation name.
            is_entity: True for companies/organisations.
        """
        return await check_sanctions(session, name, is_entity)

    return check_sanctions_list
