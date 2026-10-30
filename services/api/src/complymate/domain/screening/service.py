"""Screening service: screens a client and its parties against current watchlists."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any, Protocol
from uuid import UUID

from complymate.domain.screening.matcher import DEFAULT_THRESHOLD, best_match, normalize


@dataclass
class ScreenSubject:
    name: str
    entity: bool
    dob: str | None = None
    party_id: UUID | None = None


@dataclass
class Candidate:
    entry_id: UUID
    source: str
    primary_name: str
    names: list[str]
    entity_type: str
    dob: str | None


@dataclass
class PotentialMatch:
    subject: ScreenSubject
    candidate: Candidate
    score: float
    method: str
    matched_name: str


@dataclass
class ScreeningOutcome:
    subjects: list[ScreenSubject]
    matches: list[PotentialMatch] = field(default_factory=list)


class CandidateSource(Protocol):
    async def candidates_for(self, normalized_name: str, limit: int = 50) -> list[Candidate]: ...


def subjects_for_client(client: dict[str, Any], parties: Iterable[dict[str, Any]]) -> list[ScreenSubject]:
    entity = client["client_type"] != "individual"
    subjects = [ScreenSubject(client["display_name"], entity, client.get("date_of_birth"))]
    if client.get("legal_name") and client["legal_name"] != client["display_name"]:
        subjects.append(ScreenSubject(client["legal_name"], entity, client.get("date_of_birth")))
    for p in parties:
        subjects.append(ScreenSubject(p["full_name"], bool(p.get("is_entity")), p.get("date_of_birth"), p.get("id")))
    return subjects


async def screen(
    subjects: list[ScreenSubject], source: CandidateSource, threshold: float = DEFAULT_THRESHOLD
) -> ScreeningOutcome:
    outcome = ScreeningOutcome(subjects=subjects)
    for subject in subjects:
        norm = normalize(subject.name, entity=subject.entity)
        if not norm:
            continue
        for cand in await source.candidates_for(norm):
            # An individual should not match an entity record and vice versa.
            if (cand.entity_type == "entity") != subject.entity:
                continue
            result = best_match(
                subject.name,
                cand.names,
                entity=subject.entity,
                query_dob=str(subject.dob) if subject.dob else None,
                entry_dob=cand.dob,
            )
            if result.score >= threshold:
                outcome.matches.append(PotentialMatch(subject, cand, result.score, result.method, result.matched_name))
    outcome.matches.sort(key=lambda m: -m.score)
    return outcome
