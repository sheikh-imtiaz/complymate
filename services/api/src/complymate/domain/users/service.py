"""User and membership rules."""

from __future__ import annotations

from complymate.domain.errors import Conflict, Forbidden


def assert_can_change_role(actor_role: str | None, target_current_role: str, new_role: str, owner_count: int) -> None:
    if target_current_role == "owner" and new_role != "owner" and owner_count <= 1:
        raise Conflict("a firm must keep at least one owner")
    if new_role == "owner" and actor_role != "owner":
        raise Forbidden("only an owner can grant the owner role")


def assert_can_deactivate(target_role: str, owner_count: int, actor_id: str, target_id: str) -> None:
    if actor_id == target_id:
        raise Conflict("you cannot deactivate yourself")
    if target_role == "owner" and owner_count <= 1:
        raise Conflict("a firm must keep at least one owner")
