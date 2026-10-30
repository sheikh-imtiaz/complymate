"""Domain errors. The API layer maps them to HTTP status codes."""


class DomainError(Exception):
    code = "domain_error"


class NotFound(DomainError):
    code = "not_found"


class Forbidden(DomainError):
    code = "forbidden"


class Conflict(DomainError):
    code = "conflict"


class ValidationFailed(DomainError):
    code = "validation_failed"


class StepUpRequired(DomainError):
    code = "step_up_mfa_required"


class FourEyesViolation(Forbidden):
    code = "four_eyes_violation"


class PlanLimitReached(DomainError):
    code = "plan_limit_reached"
