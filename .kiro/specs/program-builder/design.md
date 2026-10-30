# AML/CTF Program Builder — design

## Components

* `domain/programs/{interview,approval,service,export}.py`
* `api/routers/programs.py`
* workers/draft_program.py + Step Functions program_draft
* agent/tools/draft_section.py, prompts/program_drafter.md
* web: program/*, components/program/*

## Cross-cutting

* Permission declared on every route (`require`), RLS on every table, audit event on every change.
* Works with `CLOUD_PROVIDER=local` (fakes) for tests; AWS and Azure via ports and adapters.

See `docs/architecture/overview.md` and `docs/rbac-matrix.md`.
