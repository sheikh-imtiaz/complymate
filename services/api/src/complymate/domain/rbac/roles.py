"""System roles from the permission matrix. Stored in the `roles` / `role_permissions` tables at migration
time so a firm can later copy and customise them (custom roles, Practice plan)."""

from __future__ import annotations

from dataclasses import dataclass

from complymate.domain.rbac.permissions import P, own, shared

EVERYONE = [P.TASK_READ, P.TASK_UPDATE, P.COMMENT_CREATE, P.COMMENT_READ, P.CHAT_USE, P.NOTIFICATION_READ]


@dataclass(frozen=True)
class RoleDef:
    key: str
    name: str
    description: str
    permissions: frozenset[str]


def _r(key: str, name: str, description: str, perms: list[str]) -> RoleDef:
    return RoleDef(key, name, description, frozenset(str(p) for p in perms))


OWNER = _r(
    "owner",
    "Firm Owner",
    "Billing, users, all data, sign-off of the AML/CTF program",
    [
        *EVERYONE,
        P.SHARE_CREATE,
        P.FIRM_CREATE,
        P.FIRM_READ,
        P.FIRM_UPDATE,
        P.PROGRAM_CREATE,
        P.PROGRAM_READ,
        P.PROGRAM_UPDATE,
        P.PROGRAM_APPROVE,
        P.PROGRAM_EXPORT,
        P.CLIENT_CREATE,
        P.CLIENT_READ,
        P.CLIENT_UPDATE,
        P.CLIENT_DELETE,
        P.CLIENT_EXPORT,
        P.DOCUMENT_READ,
        P.RISK_READ,
        P.RISK_UPDATE,
        P.RISK_APPROVE,
        P.SCREENING_READ,
        P.SMR_READ,
        P.TRAINING_CREATE,
        P.TRAINING_READ,
        P.TRAINING_UPDATE,
        P.TRAINING_DELETE,
        P.USER_CREATE,
        P.USER_READ,
        P.USER_UPDATE,
        P.USER_DELETE,
        P.AUDIT_READ,
        P.AUDIT_EXPORT,
        P.REPORT_READ,
        P.REPORT_EXPORT,
        P.BILLING_CREATE,
        P.BILLING_READ,
        P.BILLING_UPDATE,
        P.SETTINGS_CREATE,
        P.SETTINGS_READ,
        P.SETTINGS_UPDATE,
    ],
)

AMLCO = _r(
    "amlco",
    "Compliance Officer (AMLCO)",
    "Program, risk decisions, suspicious matter reports, approvals",
    [
        *EVERYONE,
        P.SHARE_CREATE,
        P.FIRM_READ,
        P.FIRM_UPDATE,
        P.PROGRAM_CREATE,
        P.PROGRAM_READ,
        P.PROGRAM_UPDATE,
        P.PROGRAM_EXPORT,
        P.CLIENT_CREATE,
        P.CLIENT_READ,
        P.CLIENT_UPDATE,
        P.CLIENT_DELETE,
        P.CLIENT_EXPORT,
        P.DOCUMENT_READ,
        P.RISK_CREATE,
        P.RISK_READ,
        P.RISK_UPDATE,
        P.RISK_APPROVE,
        P.SCREENING_READ,
        P.SCREENING_UPDATE,
        P.SCREENING_APPROVE,
        P.SCREENING_CREATE,
        P.SMR_CREATE_DRAFT,
        P.SMR_CREATE,
        P.SMR_READ,
        P.SMR_UPDATE,
        P.SMR_APPROVE,
        P.SMR_EXPORT,
        P.TRAINING_CREATE,
        P.TRAINING_READ,
        P.TRAINING_UPDATE,
        P.TRAINING_DELETE,
        P.USER_READ,
        P.AUDIT_READ,
        P.AUDIT_EXPORT,
        P.REPORT_READ,
        P.REPORT_EXPORT,
        P.SETTINGS_READ,
        P.SETTINGS_UPDATE,
    ],
)

SENIOR_MANAGER = _r(
    "senior_manager",
    "Senior Manager",
    "Approve high-risk clients and program changes",
    [
        *EVERYONE,
        P.SHARE_CREATE,
        P.FIRM_READ,
        P.PROGRAM_READ,
        P.PROGRAM_APPROVE,
        P.CLIENT_READ,
        P.CLIENT_APPROVE,
        P.CLIENT_EXPORT,
        P.DOCUMENT_READ,
        P.RISK_READ,
        P.RISK_APPROVE,
        P.SCREENING_READ,
        P.SMR_READ,
        P.SMR_APPROVE,
        P.TRAINING_READ,
        P.USER_READ,
        P.AUDIT_READ,
        P.REPORT_READ,
        P.REPORT_EXPORT,
        P.SETTINGS_READ,
    ],
)

STAFF = _r(
    "staff",
    "Staff Member",
    "Onboard clients, upload documents, run screening",
    [
        *EVERYONE,
        P.FIRM_READ,
        P.PROGRAM_READ,
        P.CLIENT_CREATE,
        own(P.CLIENT_READ),
        own(P.CLIENT_UPDATE),
        P.DOCUMENT_CREATE,
        own(P.DOCUMENT_READ),
        P.RISK_CREATE,
        own(P.RISK_READ),
        P.SCREENING_CREATE,
        P.SCREENING_READ,
        P.SMR_CREATE_DRAFT,
        own(P.TRAINING_READ),
        own(P.REPORT_READ),
    ],
)

AUDITOR = _r(
    "auditor",
    "Read-only Auditor",
    "View program, clients, audit log, reports. No edits.",
    [
        P.TASK_READ,
        P.COMMENT_READ,
        P.NOTIFICATION_READ,
        P.FIRM_READ,
        P.PROGRAM_READ,
        P.PROGRAM_EXPORT,
        P.CLIENT_READ,
        P.DOCUMENT_READ_MASKED,
        P.RISK_READ,
        P.SCREENING_READ,
        P.SMR_READ,
        P.TRAINING_READ,
        P.USER_READ,
        P.AUDIT_READ,
        P.AUDIT_EXPORT,
        P.REPORT_READ,
        P.REPORT_EXPORT,
        P.SETTINGS_READ,
    ],
)

ADVISOR = _r(
    "advisor",
    "External Advisor",
    "Access only to items shared with them, time-limited",
    [
        P.COMMENT_CREATE,
        P.COMMENT_READ,
        P.NOTIFICATION_READ,
        shared(P.PROGRAM_READ),
        shared(P.CLIENT_READ),
        shared(P.RISK_READ),
        shared(P.REPORT_READ),
    ],
)

# Used while Platform Support impersonates with tenant consent: read metadata, never ID documents or SMRs.
SUPPORT_IMPERSONATION = _r(
    "support_impersonation",
    "Platform Support (impersonating)",
    "Read-only support view, time-limited",
    [
        P.FIRM_READ,
        P.PROGRAM_READ,
        P.CLIENT_READ,
        P.RISK_READ,
        P.SCREENING_READ,
        P.TRAINING_READ,
        P.USER_READ,
        P.SETTINGS_READ,
        P.TASK_READ,
        P.REPORT_READ,
        P.BILLING_READ,
    ],
)

TENANT_ROLES: dict[str, RoleDef] = {r.key: r for r in (OWNER, AMLCO, SENIOR_MANAGER, STAFF, AUDITOR, ADVISOR)}

# Platform roles (vendor staff)
PLATFORM_ROLES: dict[str, frozenset[str]] = {
    "super_admin": frozenset(str(p) for p in P if p.value.startswith("platform:")),
    "platform_support": frozenset(
        {P.PLATFORM_TENANTS_READ, P.PLATFORM_IMPERSONATE, P.PLATFORM_HEALTH_READ, P.PLATFORM_USAGE_READ}
    ),
    "content_manager": frozenset({P.PLATFORM_CONTENT_UPDATE, P.PLATFORM_AI_QUALITY}),
}

# Roles allowed to see SMRs at all (strict access + tipping-off warning)
SMR_ROLES = frozenset({"owner", "amlco", "senior_manager"})
