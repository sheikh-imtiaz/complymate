"""Permission strings: `resource:action`, optionally scoped `resource:action:own|shared`.

C = create, R = read, U = update, D = delete, A = approve, X = export (see docs/rbac-matrix.md).
"""

from __future__ import annotations

from enum import StrEnum


class P(StrEnum):
    FIRM_CREATE = "firm:create"
    FIRM_READ = "firm:read"
    FIRM_UPDATE = "firm:update"

    PROGRAM_CREATE = "program:create"
    PROGRAM_READ = "program:read"
    PROGRAM_UPDATE = "program:update"
    PROGRAM_APPROVE = "program:approve"
    PROGRAM_EXPORT = "program:export"

    CLIENT_CREATE = "client:create"
    CLIENT_READ = "client:read"
    CLIENT_UPDATE = "client:update"
    CLIENT_DELETE = "client:delete"
    CLIENT_APPROVE = "client:approve"
    CLIENT_EXPORT = "client:export"

    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_READ_MASKED = "document:read_masked"

    RISK_CREATE = "risk:create"
    RISK_READ = "risk:read"
    RISK_UPDATE = "risk:update"
    RISK_APPROVE = "risk:approve"

    SCREENING_CREATE = "screening:create"
    SCREENING_READ = "screening:read"
    SCREENING_UPDATE = "screening:update"
    SCREENING_APPROVE = "screening:approve"

    SMR_CREATE_DRAFT = "smr:create_draft"
    SMR_CREATE = "smr:create"
    SMR_READ = "smr:read"
    SMR_UPDATE = "smr:update"
    SMR_APPROVE = "smr:approve"
    SMR_EXPORT = "smr:export"

    TRAINING_CREATE = "training:create"
    TRAINING_READ = "training:read"
    TRAINING_UPDATE = "training:update"
    TRAINING_DELETE = "training:delete"

    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"

    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    REPORT_READ = "report:read"
    REPORT_EXPORT = "report:export"

    BILLING_CREATE = "billing:create"
    BILLING_READ = "billing:read"
    BILLING_UPDATE = "billing:update"

    SETTINGS_CREATE = "settings:create"
    SETTINGS_READ = "settings:read"
    SETTINGS_UPDATE = "settings:update"

    # Everyone in a tenant
    TASK_READ = "task:read"
    TASK_UPDATE = "task:update"
    COMMENT_CREATE = "comment:create"
    COMMENT_READ = "comment:read"
    SHARE_CREATE = "share:create"
    CHAT_USE = "chat:use"
    NOTIFICATION_READ = "notification:read"

    # Platform (vendor)
    PLATFORM_TENANTS_READ = "platform:tenants:read"
    PLATFORM_TENANTS_UPDATE = "platform:tenants:update"
    PLATFORM_FLAGS_UPDATE = "platform:flags:update"
    PLATFORM_CONTENT_UPDATE = "platform:content:update"
    PLATFORM_IMPERSONATE = "platform:impersonate"
    PLATFORM_HEALTH_READ = "platform:health:read"
    PLATFORM_USAGE_READ = "platform:usage:read"
    PLATFORM_AI_QUALITY = "platform:ai_quality"
    PLATFORM_AUDIT_READ = "platform:audit:read"
    PLATFORM_BREAK_GLASS = "platform:break_glass"


def own(p: P) -> str:
    return f"{p.value}:own"


def shared(p: P) -> str:
    return f"{p.value}:shared"


ALL_PERMISSIONS: frozenset[str] = frozenset(p.value for p in P)

# Actions that need step-up MFA within the last STEP_UP_MFA_SECONDS.
STEP_UP_PERMISSIONS: frozenset[str] = frozenset(
    {
        P.CLIENT_APPROVE,
        P.RISK_APPROVE,
        P.SMR_APPROVE,
        P.SMR_EXPORT,
        P.USER_UPDATE,
        P.USER_DELETE,
        P.USER_CREATE,
        P.CLIENT_EXPORT,
        P.AUDIT_EXPORT,
        P.REPORT_EXPORT,
        P.PROGRAM_APPROVE,
        P.PROGRAM_EXPORT,
        P.PLATFORM_IMPERSONATE,
        P.PLATFORM_BREAK_GLASS,
    }
)
