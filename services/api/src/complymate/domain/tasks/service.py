"""Tasks: due dates and escalation to the AMLCO."""

from __future__ import annotations

from datetime import date, timedelta

TASK_TYPES = ("approval", "review", "rescreen_match", "edd", "training", "program_review", "smr", "general")
ESCALATE_AFTER_DAYS = 3

DEFAULT_DUE_DAYS = {
    "approval": 3,
    "review": 30,
    "rescreen_match": 2,
    "edd": 10,
    "training": 14,
    "program_review": 30,
    "smr": 1,
    "general": 7,
}


def default_due(task_type: str, today: date | None = None) -> date:
    return (today or date.today()) + timedelta(days=DEFAULT_DUE_DAYS.get(task_type, 7))


def needs_escalation(due: date | None, status: str, escalated: bool, today: date | None = None) -> bool:
    if status != "open" or escalated or due is None:
        return False
    return (today or date.today()) > due + timedelta(days=ESCALATE_AFTER_DAYS)
