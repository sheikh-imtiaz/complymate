# Billing and plan limits — design

## Components

* `domain/billing/{plans,usage,limits}.py`
* `application/usage.py`
* `routers/{billing,webhooks_stripe}.py`
* migration 0012

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
