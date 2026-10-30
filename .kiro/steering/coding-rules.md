---
inclusion: always
---
# Coding rules

* Domain code (`complymate/domain`) is pure: no SQLAlchemy, no cloud SDKs, no FastAPI. Test it with unit tests.
* Every API route declares its permission: `ctx: Ctx = Depends(require(P.SOMETHING))`. Use `load_client` (or an
  equivalent ABAC check) for `own`/`shared` scopes.
* Every business change records an audit event via `ctx.record(Action.X, "resource_type", id, before=…, after=…)`.
  Don't put raw identity data in `before`/`after`.
* New tenant tables: `tenant_id uuid NOT NULL`, an index on it, and an RLS policy in a migration (see 0013).
* Migrations are hand-written SQL in `migrations/versions/NNNN_*.py`; keep SQLAlchemy models in sync.
* Errors: raise `domain.errors.*` (NotFound, Forbidden, Conflict, ValidationFailed, StepUpRequired, PlanLimitReached).
* Python: ruff + mypy clean; async everywhere in request paths; `asyncio.to_thread` around blocking SDK calls.
* Frontend: fetch through `lib/api-client.ts`; gate UI with `usePermission`, but never rely on it for security.
* Never render model output as HTML in the browser; render text.
