"""Comments on clients, program sections and SMR drafts."""

from __future__ import annotations

from complymate.domain.errors import Forbidden, ValidationFailed

COMMENTABLE = {"client", "program_section", "smr_case", "program_version", "task"}
MAX_LENGTH = 5000


def validate(resource_type: str, body: str) -> str:
    if resource_type not in COMMENTABLE:
        raise ValidationFailed(f"comments are not supported on {resource_type}")
    body = (body or "").strip()
    if not body:
        raise ValidationFailed("comment is empty")
    if len(body) > MAX_LENGTH:
        raise ValidationFailed("comment is too long")
    return body


def required_read_permission(resource_type: str) -> str:
    return {
        "client": "client:read",
        "program_section": "program:read",
        "program_version": "program:read",
        "smr_case": "smr:read",
        "task": "task:read",
    }[resource_type]


def assert_can_edit(author_id: str, actor_id: str) -> None:
    if author_id != actor_id:
        raise Forbidden("you can only edit your own comments")
