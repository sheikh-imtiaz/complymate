"""Notification kinds and email routing."""

from __future__ import annotations

from dataclasses import dataclass

EMAIL_KINDS = frozenset(
    {
        "task_assigned",
        "task_escalated",
        "mention",
        "approval_requested",
        "screening_match",
        "review_due",
        "training_overdue",
        "report_ready",
        "invite",
    }
)


@dataclass(frozen=True)
class NotificationSpec:
    kind: str
    title: str
    body: str
    link: str | None = None

    @property
    def send_email(self) -> bool:
        return self.kind in EMAIL_KINDS


def for_task(title: str, link: str | None, escalated: bool = False) -> NotificationSpec:
    kind = "task_escalated" if escalated else "task_assigned"
    prefix = "Overdue task escalated" if escalated else "New task"
    return NotificationSpec(kind, f"{prefix}: {title}", title, link)


def for_mention(author: str, resource: str, link: str | None) -> NotificationSpec:
    return NotificationSpec("mention", f"{author} mentioned you", f"You were mentioned on {resource}.", link)
