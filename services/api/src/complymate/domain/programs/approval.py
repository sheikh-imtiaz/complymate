"""Program approval workflow: draft → AMLCO review → Senior Manager / Owner sign-off → approved (locked).

Four-eyes: the person who submitted the version cannot sign it off.
"""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from complymate.domain.errors import Conflict, Forbidden
from complymate.domain.rbac.policy import assert_four_eyes

TRANSITIONS: dict[str, set[str]] = {
    "draft": {"in_review"},
    "in_review": {"awaiting_signoff", "draft"},
    "awaiting_signoff": {"approved", "draft"},
    "approved": {"superseded"},
    "superseded": set(),
}


@dataclass
class VersionState:
    status: str
    created_by: UUID | None
    submitted_by: UUID | None
    reviewed_by: UUID | None
    locked: bool


def _move(state: VersionState, to: str) -> None:
    if state.locked:
        raise Conflict("this version is approved and locked; create a new version to make changes")
    if to not in TRANSITIONS[state.status]:
        raise Conflict(f"cannot move program from {state.status} to {to}")
    state.status = to


def submit_for_review(state: VersionState, actor: UUID) -> VersionState:
    _move(state, "in_review")
    state.submitted_by = actor
    return state


def amlco_review(state: VersionState, actor: UUID, actor_role: str, approve: bool) -> VersionState:
    if actor_role not in ("amlco", "owner"):
        raise Forbidden("only the AML/CTF compliance officer can review the program")
    _move(state, "awaiting_signoff" if approve else "draft")
    state.reviewed_by = actor if approve else None
    return state


def sign_off(state: VersionState, actor: UUID, actor_role: str, approve: bool) -> VersionState:
    if actor_role not in ("senior_manager", "owner"):
        raise Forbidden("program sign-off needs a senior manager or the firm owner")
    if approve:
        assert_four_eyes(state.submitted_by, actor)
        _move(state, "approved")
        state.locked = True
    else:
        _move(state, "draft")
    return state
