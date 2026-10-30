# Tenant admin and platform admin panels — requirements

## User story

As a firm owner I manage users, roles and security; as ComplyMate staff we run the platform without seeing client documents.

## Acceptance criteria (EARS)

1. Owners SHALL invite, deactivate, reset MFA and change roles (step-up, audited); a firm SHALL keep at least one owner.
2. Owners SHALL configure MFA requirement, session timeout, IP allow-list (Practice), retention (≥7 years), branding and integrations.
3. Platform staff SHALL list tenants, suspend/reactivate, set feature flags, manage the rule library, templates and quiz reviews, and view usage/cost, AI quality and system health.
4. Support impersonation SHALL require the owner's consent, a reason and a time limit (≤60 minutes) and be read-only.
5. Platform contexts SHALL NOT access client documents, parties or SMRs (RLS).
6. All platform actions SHALL be written to the platform audit chain.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
