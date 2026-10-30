"""Loads versioned YAML rule files from complymate/rules/{au,nz}."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DEFAULT_RULES_DIR = Path(__file__).resolve().parents[2] / "rules"


@dataclass(frozen=True)
class RuleSet:
    jurisdiction: str
    version: str
    home_country: str
    thresholds: dict[str, int]
    lists: dict[str, list[str]]
    factors: list[dict[str, Any]]
    review_months: dict[str, int]
    reminder_days_before: int
    program_review_months: int
    cdd: dict[str, Any]


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        data: dict[str, Any] = yaml.safe_load(fh)
    return data


@lru_cache(maxsize=8)
def load_rules(jurisdiction: str = "AU", rules_dir: str | None = None) -> RuleSet:
    base = Path(rules_dir) if rules_dir else DEFAULT_RULES_DIR
    folder = base / jurisdiction.lower()
    risk = _load(folder / "risk_factors.yaml")
    review = _load(folder / "review_periods.yaml")
    cdd = _load(folder / "cdd_requirements.yaml")
    if not (risk["version"] == review["version"] == cdd["version"]):
        raise ValueError(f"rule file versions differ in {folder}")
    return RuleSet(
        jurisdiction=risk["jurisdiction"],
        version=risk["version"],
        home_country=risk.get("home_country", jurisdiction),
        thresholds=risk["thresholds"],
        lists={
            k: [str(x).upper() if len(str(x)) == 2 else str(x) for x in v] for k, v in risk.get("lists", {}).items()
        },
        factors=risk["factors"],
        review_months=review["review_months"],
        reminder_days_before=review.get("reminder_days_before", 30),
        program_review_months=review.get("program_review_months", 12),
        cdd=cdd,
    )
