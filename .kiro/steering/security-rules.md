---
inclusion: always
---
# Security rules

* Two locks on tenant data: RBAC dependency + PostgreSQL RLS. Never connect the app with the owner role.
* `audit_events` is append-only. Never write UPDATE/DELETE against it, never add a migration that weakens grants.
* Sensitive actions require step-up MFA: add new ones to `STEP_UP_PERMISSIONS`.
* Four-eyes: a person cannot approve a high-risk decision they created (`assert_four_eyes`).
* No PII in logs, metric dimensions, tags or exception messages. Use the structlog logger; the PII filter is a
  safety net, not a licence.
* SMRs: only owner/AMLCO/senior manager see cases; show the tipping-off warning; the agent never submits reports.
* Secrets come from the `SecretStore` port or environment set by Terraform. Never commit secrets.
* Documents are envelope-encrypted with the tenant data key before upload (`application/documents.py`).
* AI outputs show sources; a human accepts or rejects suggestions; record `ai` details in the audit event.
