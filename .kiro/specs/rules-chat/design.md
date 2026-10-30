# Ask the Rules chat — design

## Components

* agent/{factory,guardrails}.py, agent/rag/*, agent/tools/*
* `api/ws/chat.py (native + API Gateway WebSocket)`
* `routers/chat.py (SSE + JSON)`
* Bedrock Guardrail (infra modules/aws/ai)

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
