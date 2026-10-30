# Tenant admin and platform admin panels — design

## Components

* `routers/{users,roles,invitations,api_keys,tenants,platform_admin}.py`
* `domain/platform/*`
* apps/web admin/*
* `apps/platform-admin`

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
