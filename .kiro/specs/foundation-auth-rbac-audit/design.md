# Foundation: auth, tenants, RBAC, RLS, audit — design

## Components

* `api/deps.py (authenticate, get_ctx, require)`
* `domain/rbac/{permissions,roles,policy}.py`
* migrations 0001, 0003, 0004, 0013
* `domain/audit/{hash_chain,service}.py`
* `workers/{verify_audit_chain,archive_audit_events}.py`

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
