"""Compliance dashboard aggregation (pure: takes counts, returns the view model)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DashboardData:
    clients_by_risk: dict[str, int] = field(default_factory=dict)
    clients_by_status: dict[str, int] = field(default_factory=dict)
    overdue_reviews: int = 0
    open_matches: int = 0
    open_tasks: int = 0
    overdue_tasks: int = 0
    training_total: int = 0
    training_completed: int = 0
    training_overdue: int = 0
    program_status: str | None = None
    program_next_review: str | None = None
    open_smrs: int | None = None  # only for SMR roles

    def as_dict(self) -> dict[str, Any]:
        completion = round(100 * self.training_completed / self.training_total, 1) if self.training_total else None
        alerts = []
        if self.open_matches:
            alerts.append({"level": "warning", "text": f"{self.open_matches} screening match(es) to review"})
        if self.overdue_reviews:
            alerts.append({"level": "warning", "text": f"{self.overdue_reviews} client review(s) overdue"})
        if self.training_overdue:
            alerts.append({"level": "info", "text": f"{self.training_overdue} training assignment(s) overdue"})
        if self.program_status not in ("approved",):
            alerts.append({"level": "critical", "text": "Your AML/CTF program is not approved yet"})
        return {
            "clients_by_risk": {k: self.clients_by_risk.get(k, 0) for k in ("low", "medium", "high", "unassessed")},
            "clients_by_status": self.clients_by_status,
            "overdue_reviews": self.overdue_reviews,
            "open_matches": self.open_matches,
            "open_tasks": self.open_tasks,
            "overdue_tasks": self.overdue_tasks,
            "training": {
                "total": self.training_total,
                "completed": self.training_completed,
                "overdue": self.training_overdue,
                "completion_percent": completion,
            },
            "program": {"status": self.program_status, "next_review": self.program_next_review},
            "open_smrs": self.open_smrs,
            "alerts": alerts,
        }
