"""Client lifecycle: pending → approved / declined → exited. High-risk approval needs a second person."""

from __future__ import annotations

from uuid import UUID

from complymate.domain.errors import Conflict, ValidationFailed
from complymate.domain.rbac.policy import assert_four_eyes

STATUSES = ("pending", "approved", "declined", "exited")
CLIENT_TYPES = ("individual", "company", "trust", "partnership")

TRANSITIONS = {
    "pending": {"approved", "declined"},
    "approved": {"exited", "pending"},  # back to pending on re-review trigger
    "declined": {"pending"},
    "exited": set(),
}


def assert_transition(current: str, new: str) -> None:
    if new not in TRANSITIONS.get(current, set()):
        raise Conflict(f"cannot move client from {current} to {new}")


def assert_can_approve(
    *,
    risk_level: str | None,
    risk_assessed_by: UUID | None,
    created_by: UUID | None,
    approver: UUID,
    open_matches: int,
    true_match: bool,
    open_edd_tasks: int,
    screened: bool,
) -> None:
    if not screened:
        raise ValidationFailed("screen the client before approval")
    if true_match:
        raise Conflict("client has a confirmed sanctions match; decline and consider an SMR")
    if open_matches:
        raise ValidationFailed("resolve open screening matches first")
    if risk_level is None:
        raise ValidationFailed("run the risk assessment first")
    if risk_level == "high":
        if open_edd_tasks:
            raise ValidationFailed("complete enhanced due diligence tasks first")
        assert_four_eyes(created_by, approver)
        assert_four_eyes(risk_assessed_by, approver)


def display_name(client_type: str, given_names: str | None, family_name: str | None, legal_name: str | None) -> str:
    if client_type == "individual":
        name = " ".join(x for x in (given_names, family_name) if x)
    else:
        name = legal_name or ""
    if not name.strip():
        raise ValidationFailed("client name is required")
    return name.strip()
