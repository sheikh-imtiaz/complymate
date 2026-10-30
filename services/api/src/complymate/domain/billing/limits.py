"""Hard limits and soft warnings (80%)."""

from __future__ import annotations

from dataclasses import dataclass

from complymate.domain.billing.plans import Plan
from complymate.domain.errors import PlanLimitReached

SOFT_WARNING_RATIO = 0.8


@dataclass(frozen=True)
class LimitCheck:
    metric: str
    used: int
    limit: int
    warning: bool
    blocked: bool

    @property
    def message(self) -> str | None:
        if self.blocked:
            return f"Plan limit reached for {self.metric} ({self.used}/{self.limit}). Upgrade to continue."
        if self.warning:
            return f"You have used {self.used} of {self.limit} {self.metric} this period."
        return None


def check(plan: Plan, metric: str, used: int, adding: int = 1) -> LimitCheck:
    limit = plan.max_users if metric == "users" else plan.limits.get(metric, 0)
    if limit <= 0:
        return LimitCheck(metric, used, limit, False, False)
    after = used + adding
    return LimitCheck(metric, used, limit, after >= limit * SOFT_WARNING_RATIO, after > limit)


def enforce(plan: Plan, metric: str, used: int, adding: int = 1) -> LimitCheck:
    result = check(plan, metric, used, adding)
    if result.blocked:
        raise PlanLimitReached(result.message or "plan limit reached")
    return result


def has_feature(plan: Plan, feature: str) -> bool:
    return feature in plan.features
