"""Screens a client and its parties against the current watchlists and stores the run and matches."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from complymate.db.models import Client, ScreeningMatch, ScreeningRun
from complymate.db.repositories.clients import ClientRepo
from complymate.db.repositories.screening import ScreeningRepo
from complymate.domain.screening.service import screen, subjects_for_client


async def screen_client(
    session: AsyncSession, client: Client, *, trigger: str, actor_id: UUID | None
) -> tuple[ScreeningRun, list[ScreeningMatch]]:
    repo = ScreeningRepo(session)
    parties = await ClientRepo(session).parties(client.id)
    subjects = subjects_for_client(
        {
            "client_type": client.client_type,
            "display_name": client.display_name,
            "legal_name": client.legal_name,
            "date_of_birth": client.date_of_birth.isoformat() if client.date_of_birth else None,
        },
        [
            {
                "id": p.id,
                "full_name": p.full_name,
                "is_entity": p.is_entity,
                "date_of_birth": p.date_of_birth.isoformat() if p.date_of_birth else None,
            }
            for p in parties
        ],
    )
    versions = await repo.current_versions()
    outcome = await screen(subjects, repo)
    run = ScreeningRun(
        tenant_id=client.tenant_id,
        client_id=client.id,
        trigger=trigger,
        watchlist_version_ids=[str(v.id) for v in versions],
        screened_names=[s.name for s in subjects],
        status="completed",
        pep_declared=client.is_pep,
        started_by=actor_id,
        completed_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()
    new_matches: list[ScreeningMatch] = []
    seen: set[tuple[UUID, str]] = set()
    for m in outcome.matches:
        key = (m.candidate.entry_id, m.subject.name)
        if key in seen:
            continue
        seen.add(key)
        prior = await repo.existing_decision(client.id, m.candidate.entry_id, m.subject.name)
        if prior == "false_positive":
            continue  # same name/entry already cleared by a reviewer
        match = ScreeningMatch(
            tenant_id=client.tenant_id,
            run_id=run.id,
            client_id=client.id,
            party_id=m.subject.party_id,
            entry_id=m.candidate.entry_id,
            subject_name=m.subject.name,
            matched_name=m.matched_name,
            score=m.score,
            method=m.method,
            status="true_match" if prior == "true_match" else "open",
        )
        session.add(match)
        new_matches.append(match)
    run.match_count = len(new_matches)
    client.last_screened_at = run.completed_at
    await session.flush()
    return run, new_matches
