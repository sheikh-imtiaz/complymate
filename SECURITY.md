# Security Policy

## Reporting a vulnerability

Email security@complymate.example with details and steps to reproduce. Do not open a public issue.
We acknowledge within 2 business days and aim to fix critical issues within 7 days.

## Scope

* `services/api`, `apps/web`, `apps/platform-admin`, `infra/terraform`.
* Out of scope: denial of service testing, social engineering, third-party services (Stripe, AWS).

## Security controls (summary)

* OWASP ASVS Level 2 target. Pen test before first large customer.
* Tenant isolation: RBAC dependency on every route + PostgreSQL RLS (`app.tenant_id`).
* Step-up MFA (last 10 minutes) for: approving high-risk clients, submitting SMRs, changing roles, exports.
* Four-eyes rule for high-risk decisions.
* Append-only, hash-chained audit log with S3 Object Lock (compliance mode, 7 years).
* No PII in system logs (structlog PII filter).
* Encryption: TLS 1.2+, KMS at rest, per-tenant data keys for documents.
* CI: Trivy, Checkov, pip-audit, npm audit, Dependabot.

See `docs/security/` for the threat model, data classification and incident response plan.
