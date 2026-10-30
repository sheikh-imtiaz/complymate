"""Tool: explain how the deterministic risk engine would rate a described client (no data is saved).
The engine — not the model — produces the rating."""

from __future__ import annotations

from typing import Any

from complymate.domain.risk.engine import score
from complymate.domain.risk.rules_loader import load_rules


def score_risk(facts: dict[str, Any], jurisdiction: str = "AU") -> dict[str, Any]:
    rules = load_rules(jurisdiction)
    base = {
        "client_type": "individual",
        "countries": [],
        "services": [],
        "channel": "face_to_face",
        "source_of_funds_verified": True,
        "beneficial_owners_identified": True,
        "entity_age_months": 999,
    }
    return score({**base, **facts}, rules).as_dict()


def make_tool(jurisdiction: str) -> Any:
    from strands import tool

    @tool
    def explain_risk_rating(
        client_type: str = "individual",
        countries: list[str] | None = None,
        services: list[str] | None = None,
        channel: str = "face_to_face",
        is_pep: bool = False,
    ) -> dict[str, Any]:
        """Show how the firm's rule-based risk engine would rate a hypothetical client.

        Args:
            client_type: individual, company, trust or partnership.
            countries: ISO country codes linked to the client.
            services: designated service codes requested.
            channel: face_to_face, non_face_to_face or intermediary.
            is_pep: whether the client is a politically exposed person.
        """
        return score_risk(
            {
                "client_type": client_type,
                "countries": [c.upper() for c in countries or []],
                "services": services or [],
                "channel": channel,
                "is_pep": is_pep,
            },
            jurisdiction,
        )

    return explain_risk_rating
