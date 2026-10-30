# complymate (API + workers)

FastAPI app, worker entrypoints, Strands agent and Alembic migrations. See the root README for setup.

* `src/complymate/domain` — pure business logic (no cloud SDK, no SQLAlchemy).
* `src/complymate/ports` — interfaces. `adapters/{aws,azure,local}` implement them.
* `src/complymate/container.py` — wires adapters from `CLOUD_PROVIDER`.
* `src/complymate/lambda_handlers.py` — AWS Lambda handlers (API via Mangum, workers, WebSocket chat).
