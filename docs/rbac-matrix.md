# RBAC matrix

C = create, R = read, U = update, D = delete, A = approve, X = export. "own" = records the user created or is
assigned to. "shared" = items shared with an External Advisor (time-limited). Source of truth in code:
`services/api/src/complymate/domain/rbac/roles.py` (seeded into `roles` / `role_permissions` by migration 0003).

| Resource | Owner | AMLCO | Sr Manager | Staff | Auditor | Advisor |
|---|---|---|---|---|---|---|
| Firm profile | CRU | RU | R | R | R | — |
| AML/CTF program | CRUAX | CRUX | RA | R | RX | R (shared) |
| Clients | CRUDX | CRUDX | RAX | CRU (own) | R | R (shared) |
| ID documents | R | R | R | CR (own) | R (masked) | — |
| Risk assessment | RUA | CRUA | RA | CR (own) | R | R (shared) |
| Screening (sanctions/PEP) | R | RUA | R | CR | R | — |
| Suspicious matter reports | R | CRUAX | RA | C (draft only) | R | — |
| Training and quizzes | CRUD | CRUD | R | R (own results) | R | — |
| Users and roles | CRUD | R | R | — | R | — |
| Audit log | RX | RX | R | — | RX | — |
| Reports | RX | RX | RX | R (own) | RX | R (shared) |
| Billing | CRU | — | — | — | — | — |
| Settings and integrations | CRU | RU | R | — | R | — |

## Mapping to permission strings

| Matrix | Permission |
|---|---|
| Clients A (approve high-risk client) | `risk:approve` on `POST /clients/{id}/approve` (four-eyes enforced) |
| Program A | `program:approve` (sign-off); AMLCO review is `program:update` + role `amlco` |
| SMR C (draft) | `smr:create_draft`; full access `smr:read`, decide `smr:approve`, export `smr:export` |
| ID documents (masked) | `document:read_masked` (OCR fields masked, download refused) |

## Attribute rules (ABAC)

* **own** — `created_by` or `assigned_to` equals the user (`check_record_access`).
* **shared** — an active row in `shares` (not revoked, not expired) for the user and resource.
* **tenant match** — header tenant must be one of the user's active memberships; RLS enforces it again.
* **MFA verified** — `STEP_UP_PERMISSIONS` need MFA within `STEP_UP_MFA_SECONDS` (600): approve high-risk client,
  program sign-off, SMR decide/export, user/role changes, exports, impersonation.

## Platform roles (vendor)

| Role | Permissions |
|---|---|
| Super Admin | all `platform:*`, break-glass (`X-Break-Glass-Reason`, always audited) |
| Platform Support | tenant metadata, health, usage; impersonation only with tenant owner consent + time limit; never ID documents or SMRs (RLS) |
| Content Manager | rule library, templates, quiz review, AI quality; no tenant data |
