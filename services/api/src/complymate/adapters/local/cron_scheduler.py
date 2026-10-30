"""Local cron: keeps schedules in memory. `workers.entry --serve` evaluates them every minute."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class Schedule:
    name: str
    cron: str
    task: str
    payload: dict[str, Any]


def _field_matches(expr: str, value: int) -> bool:
    for part in expr.split(","):
        step = 1
        if "/" in part:
            part, step_s = part.split("/")
            step = int(step_s)
        if part in ("*", "?"):
            if value % step == 0:
                return True
            continue
        if "-" in part:
            lo, hi = (int(x) for x in part.split("-"))
            if lo <= value <= hi and (value - lo) % step == 0:
                return True
        elif int(part) == value:
            return True
    return False


def cron_matches(cron: str, when: datetime) -> bool:
    """Matches 5-field cron (min hour dom month dow). dow: 0=Sunday."""
    minute, hour, dom, month, dow = cron.split()[:5]
    return (
        _field_matches(minute, when.minute)
        and _field_matches(hour, when.hour)
        and _field_matches(dom, when.day)
        and _field_matches(month, when.month)
        and _field_matches(dow, (when.weekday() + 1) % 7)
    )


class CronScheduler:
    def __init__(self) -> None:
        self.schedules: dict[str, Schedule] = {}

    async def upsert_schedule(self, name: str, cron: str, task: str, payload: dict[str, Any]) -> None:
        self.schedules[name] = Schedule(name, cron, task, payload)

    async def delete_schedule(self, name: str) -> None:
        self.schedules.pop(name, None)

    def due(self, when: datetime) -> list[Schedule]:
        return [s for s in self.schedules.values() if cron_matches(s.cron, when)]
