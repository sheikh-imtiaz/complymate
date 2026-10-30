# Sanctions and PEP screening — design

## Components

* `domain/screening/{matcher,service,watchlist_parser}.py`
* `db/repositories/screening.py (pg_trgm prefilter)`
* `application/screening.py`
* `workers/{refresh_watchlists,nightly_rescreen,screen_client}.py`
* `templates/screening_certificate.html`

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
