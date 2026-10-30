# Foundation: auth, tenants, RBAC, RLS, audit — requirements

## User story

As a firm owner I want my firm's data isolated, every action recorded, and sensitive actions protected by MFA, so that I can show regulators my records are reliable.

## Acceptance criteria (EARS)

1. WHEN a user signs in THE SYSTEM SHALL require MFA (Cognito MFA ON / Entra Conditional Access).
2. WHEN a request names a tenant the user is not an active member of THE SYSTEM SHALL return 403.
3. THE SYSTEM SHALL set app.tenant_id per transaction and enforce RLS on every tenant table.
4. WHEN a route is called THE SYSTEM SHALL check the declared permission (with own/shared scope) before the handler runs.
5. WHEN a STEP_UP permission is used and MFA is older than 10 minutes THE SYSTEM SHALL return 401 step_up_mfa_required.
6. WHEN a business record changes THE SYSTEM SHALL append a hash-chained audit event; the app role SHALL NOT update or delete audit events.
7. THE SYSTEM SHALL verify every audit chain nightly and alert on a break.
8. THE SYSTEM SHALL copy audit events to immutable storage (7 years) every 15 minutes.

## Out of scope

* Legal advice. ComplyMate provides general information; firms make their own decisions.
