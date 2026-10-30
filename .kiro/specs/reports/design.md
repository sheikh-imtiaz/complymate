# Reports and regulator pack — design

## Components

* `application/reports.py`
* `domain/reports/*`
* `routers/reports.py`
* `workers/{build_regulator_pack,send_scheduled_reports}.py`

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
