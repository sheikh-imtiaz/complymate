"""SQLAlchemy tables, one file per area. Import everything so metadata is complete."""

from complymate.db.models.audit import AuditArchiveCursor, AuditEventRow, ChainVerification
from complymate.db.models.billing import (
    Export,
    FeatureFlag,
    ImpersonationSession,
    PlanRow,
    ReportJob,
    StripeEvent,
    Subscription,
    UsageCounter,
)
from complymate.db.models.clients import (
    Client,
    ClientDocument,
    ClientParty,
    EddTask,
    RiskAssessment,
    RiskFactorRow,
    Verification,
)
from complymate.db.models.collaboration import Comment, Mention, Notification, PresenceHeartbeat, Share, Task
from complymate.db.models.kb import AiFeedback, ChatMessage, ChatSession, KbChunk, KbSource, LlmCall
from complymate.db.models.programs import Program, ProgramApproval, ProgramSection, ProgramVersion
from complymate.db.models.screening import ScreeningMatch, ScreeningRun, WatchlistEntryRow, WatchlistVersion
from complymate.db.models.smr import SmrCase, SmrNote
from complymate.db.models.tenants import Tenant, TenantSettings
from complymate.db.models.training import QuizAttempt, QuizQuestion, TrainingAssignment, TrainingModule
from complymate.db.models.users import ApiKey, Invitation, Membership, Role, RolePermission, User

__all__ = [
    "AiFeedback",
    "ApiKey",
    "AuditArchiveCursor",
    "AuditEventRow",
    "ChainVerification",
    "ChatMessage",
    "ChatSession",
    "Client",
    "ClientDocument",
    "ClientParty",
    "Comment",
    "EddTask",
    "Export",
    "FeatureFlag",
    "ImpersonationSession",
    "Invitation",
    "KbChunk",
    "KbSource",
    "LlmCall",
    "Membership",
    "Mention",
    "Notification",
    "PlanRow",
    "PresenceHeartbeat",
    "Program",
    "ProgramApproval",
    "ProgramSection",
    "ProgramVersion",
    "QuizAttempt",
    "QuizQuestion",
    "ReportJob",
    "RiskAssessment",
    "RiskFactorRow",
    "Role",
    "RolePermission",
    "ScreeningMatch",
    "ScreeningRun",
    "Share",
    "SmrCase",
    "SmrNote",
    "StripeEvent",
    "Subscription",
    "Task",
    "Tenant",
    "TenantSettings",
    "TrainingAssignment",
    "TrainingModule",
    "UsageCounter",
    "User",
    "Verification",
    "WatchlistEntryRow",
    "WatchlistVersion",
]
