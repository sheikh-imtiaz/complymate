"""Plans: Solo A$79/mo, Practice A$249/mo (10 users), onboarding A$299 one-off."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    price_cents: int
    max_users: int
    limits: dict[str, int] = field(default_factory=dict)
    features: frozenset[str] = frozenset()


SOLO = Plan(
    "solo",
    "Solo",
    7900,
    2,
    {"agent_turns": 300, "documents": 500, "clients": 250},
    frozenset(),
)
PRACTICE = Plan(
    "practice",
    "Practice",
    24900,
    10,
    {"agent_turns": 2000, "documents": 5000, "clients": 2500},
    frozenset({"custom_roles", "ip_allow_list", "scheduled_reports", "api_keys"}),
)
ONBOARDING_FEE_CENTS = 29900
TRIAL_DAYS = 14
CURRENCY = "aud"

PLANS = {p.code: p for p in (SOLO, PRACTICE)}


def get_plan(code: str) -> Plan:
    return PLANS.get(code, SOLO)
