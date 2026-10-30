# Client due diligence (CDD) — design

## Components

* `domain/clients/{service,ownership}.py`
* domain/risk/{engine,factors,rules_loader}.py + rules/{au,nz}/*.yaml
* `application/{documents,risk}.py`
* routers: clients, documents, risk
* `workers/ocr_document.py`

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
