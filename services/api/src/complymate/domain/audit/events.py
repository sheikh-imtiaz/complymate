"""Audit event model. Every create, update, delete, approve, export, login, permission change and AI decision."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID


class Action(StrEnum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    APPROVE = "approve"
    REJECT = "reject"
    SUBMIT = "submit"
    EXPORT = "export"
    VIEW_SENSITIVE = "view_sensitive"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    MFA_FAILED = "mfa_failed"
    PERMISSION_CHANGE = "permission_change"
    ROLE_CHANGE = "role_change"
    INVITE = "invite"
    DEACTIVATE = "deactivate"
    IMPERSONATION_START = "impersonation_start"
    IMPERSONATION_STOP = "impersonation_stop"
    BREAK_GLASS = "break_glass"
    API_KEY_USE = "api_key_use"
    AI_SUGGESTION = "ai_suggestion"
    AI_ACCEPTED = "ai_accepted"
    AI_REJECTED = "ai_rejected"
    SCREEN = "screen"
    DECIDE = "decide"
    LOCK = "lock"
    SHARE = "share"


SECURITY_ACTIONS = frozenset(
    {
        Action.LOGIN_FAILED,
        Action.MFA_FAILED,
        Action.ROLE_CHANGE,
        Action.PERMISSION_CHANGE,
        Action.IMPERSONATION_START,
        Action.IMPERSONATION_STOP,
        Action.EXPORT,
        Action.API_KEY_USE,
        Action.BREAK_GLASS,
        Action.DEACTIVATE,
    }
)


@dataclass
class AuditContext:
    actor_id: UUID | None
    actor_role: str
    tenant_id: UUID | None
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None


@dataclass
class AuditEvent:
    tenant_id: UUID | None
    actor_id: UUID | None
    actor_role: str
    action: str
    resource_type: str
    resource_id: str | None
    occurred_at: datetime
    before: dict[str, Any] | None = None
    after: dict[str, Any] | None = None
    reason: str | None = None
    ip: str | None = None
    user_agent: str | None = None
    request_id: str | None = None
    ai: dict[str, Any] | None = None  # model, prompt_version, sources, tool_calls, decision
    id: UUID | None = None
    prev_hash: str | None = None
    hash: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)
