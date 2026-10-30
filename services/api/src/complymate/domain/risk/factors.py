"""Risk facts: the flat dict the rule engine evaluates. Built from a client record, its parties and screening."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PartyFacts:
    is_pep: bool = False
    country: str | None = None
    ownership_percent: float | None = None
    is_entity: bool = False
    depth: int = 1
    verified: bool = False


@dataclass
class ClientFacts:
    client_type: str
    is_pep: bool = False
    nationality: str | None = None
    residential_country: str | None = None
    country_of_incorporation: str | None = None
    services: list[str] = field(default_factory=list)
    channel: str = "face_to_face"
    cash_intensive: bool = False
    source_of_funds_verified: bool = False
    nominee_directors: bool = False
    bearer_shares: bool = False
    incorporated_on: date | None = None
    parties: list[PartyFacts] = field(default_factory=list)
    screening_true_match: bool = False
    screening_open_matches: int = 0

    def to_facts(self, home_country: str, today: date | None = None) -> dict[str, Any]:
        today = today or date.today()
        countries = {
            c.upper()
            for c in [self.nationality, self.residential_country, self.country_of_incorporation]
            + [p.country for p in self.parties]
            if c
        }
        own_country = self.residential_country or self.country_of_incorporation
        owners = [p for p in self.parties if (p.ownership_percent or 0) >= 25 and not p.is_entity]
        entity_age = None
        if self.incorporated_on:
            entity_age = (today.year - self.incorporated_on.year) * 12 + (today.month - self.incorporated_on.month)
        return {
            "client_type": self.client_type,
            "is_pep": self.is_pep,
            "pep_any_party": any(p.is_pep for p in self.parties),
            "countries": sorted(countries),
            "foreign": own_country is not None and own_country.upper() != home_country,
            "services": list(self.services),
            "channel": self.channel,
            "cash_intensive": self.cash_intensive,
            "source_of_funds_verified": self.source_of_funds_verified,
            "nominee_directors": self.nominee_directors,
            "bearer_shares": self.bearer_shares,
            "ownership_layers": max((p.depth for p in self.parties), default=0),
            "beneficial_owners_identified": bool(owners) and all(p.verified for p in owners),
            "entity_age_months": entity_age if entity_age is not None else 999,
            "screening_true_match": self.screening_true_match,
            "screening_open_matches": self.screening_open_matches,
        }
