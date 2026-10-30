"""Deterministic risk scoring engine (rules, not AI): low / medium / high, with reasons.

Conditions:
    {fact: <name>, op: eq|neq|in|not_in|gt|gte|lt|lte|truthy|falsy|contains_any, value: <literal or {list: name}>}
    {all: [cond, ...]}   {any: [cond, ...]}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from complymate.domain.risk.rules_loader import RuleSet

LEVELS = ("low", "medium", "high")


@dataclass(frozen=True)
class Reason:
    factor_id: str
    category: str
    description: str
    points: int


@dataclass
class RiskResult:
    level: str
    score: int
    reasons: list[Reason] = field(default_factory=list)
    rules_version: str = ""
    auto_high: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "score": self.score,
            "rules_version": self.rules_version,
            "auto_high": self.auto_high,
            "reasons": [r.__dict__ for r in self.reasons],
        }


class RuleError(ValueError):
    pass


def _resolve(value: Any, rules: RuleSet) -> Any:
    if isinstance(value, dict) and "list" in value:
        try:
            return rules.lists[value["list"]]
        except KeyError as exc:
            raise RuleError(f"unknown list {value['list']}") from exc
    return value


def evaluate(cond: dict[str, Any], facts: dict[str, Any], rules: RuleSet) -> bool:
    if "all" in cond:
        return all(evaluate(c, facts, rules) for c in cond["all"])
    if "any" in cond:
        return any(evaluate(c, facts, rules) for c in cond["any"])
    op = cond.get("op")
    actual = facts.get(cond.get("fact", ""))
    expected = _resolve(cond.get("value"), rules)
    match op:
        case "truthy":
            return bool(actual)
        case "falsy":
            return not actual
        case "eq":
            return bool(actual == expected)
        case "neq":
            return bool(actual != expected)
        case "in":
            return actual in expected
        case "not_in":
            return actual not in expected
        case "gt" | "gte" | "lt" | "lte":
            if actual is None:
                return False
            return {
                "gt": actual > expected,
                "gte": actual >= expected,
                "lt": actual < expected,
                "lte": actual <= expected,
            }[op]
        case "contains_any":
            return bool(set(actual or []) & set(expected or []))
        case _:
            raise RuleError(f"unknown operator {op!r}")


def score(facts: dict[str, Any], rules: RuleSet) -> RiskResult:
    reasons: list[Reason] = []
    auto_level: str | None = None
    for factor in rules.factors:
        if evaluate(factor["when"], facts, rules):
            reasons.append(Reason(factor["id"], factor["category"], factor["description"], int(factor["points"])))
            if (lvl := factor.get("auto_level")) and (
                auto_level is None or LEVELS.index(lvl) > LEVELS.index(auto_level)
            ):
                auto_level = lvl
    total = sum(r.points for r in reasons)
    if total >= rules.thresholds["high"]:
        level = "high"
    elif total >= rules.thresholds["medium"]:
        level = "medium"
    else:
        level = "low"
    if auto_level and LEVELS.index(auto_level) > LEVELS.index(level):
        level = auto_level
    reasons.sort(key=lambda r: (-r.points, r.factor_id))
    return RiskResult(
        level=level, score=total, reasons=reasons, rules_version=rules.version, auto_high=auto_level == "high"
    )


def next_review_date(level: str, rules: RuleSet, from_date: date | None = None) -> date:
    start = from_date or date.today()
    months = rules.review_months[level]
    year = start.year + (start.month - 1 + months) // 12
    month = (start.month - 1 + months) % 12 + 1
    day = min(
        start.day,
        [
            31,
            29 if year % 4 == 0 and (year % 100 != 0 or year % 400 == 0) else 28,
            31,
            30,
            31,
            30,
            31,
            31,
            30,
            31,
            30,
            31,
        ][month - 1],
    )
    return date(year, month, day)


def edd_tasks_for(result: RiskResult, rules: RuleSet) -> list[dict[str, str]]:
    if result.level != "high":
        return []
    tasks: list[dict[str, str]] = rules.cdd.get("edd_tasks", [])
    return tasks
