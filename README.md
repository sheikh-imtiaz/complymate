# ComplyMate

AML/CTF compliance agent for small firms. Australia first (AUSTRAC Tranche 2 from 1 July 2026), then New Zealand AML/CFT.
Cloud-based, AWS first, built so it can move to Azure without a rewrite (ports and adapters; `CLOUD_PROVIDER=aws|azure|local`).

> General information, not legal advice. Have a compliance professional review program templates and rule files before launch.

## Repository layout

| Path | What |
|---|---|
| `services/api` | Python 3.12 FastAPI app + workers (one container image). Domain logic, ports, AWS/Azure/local adapters, Strands agent, Alembic migrations. |
| `apps/web` | Next.js 15 tenant app (firm users + tenant admin). |
| `apps/platform-admin` | Next.js 15 platform admin app (Super Admin / Support / Content Manager). |
| `packages/ui` | Shared shadcn/ui components. |
| `packages/api-types` | TypeScript types generated from `docs/api/openapi.json`. |
| `packages/config` | Shared ESLint / tsconfig / Tailwind config. |
| `infra/terraform` | Terraform (OpenTofu compatible) modules for AWS and Azure, per-environment stacks. |
| `docs` | Architecture, ADRs, security, runbooks, RBAC matrix. |
| `.kiro` | Kiro steering + specs. |

## Quick start (local)

Requirements: Docker, Python 3.12 + [uv](https://docs.astral.sh/uv/), Node 22 + pnpm 9.

```bash
cp .env.example .env
make up            # Postgres+pgvector, MinIO, LocalStack, Mailpit
make api-install   # uv sync
make migrate       # alembic upgrade head (runs as owner role, creates app role)
make seed          # demo tenant, users, watchlist sample, rule library
make api           # http://localhost:8000/docs
pnpm install
make web           # http://localhost:3000   (tenant app)
make admin         # http://localhost:3001   (platform admin)
```

Local mode uses `CLOUD_PROVIDER=local`: a fake LLM and embeddings, MinIO storage, in-memory queue,
Mailpit email, a dev identity provider (sign in as any seeded user), and a file-based audit sink.

Seeded users (password-less dev sign-in): `owner@demo.test`, `amlco@demo.test`, `manager@demo.test`,
`staff@demo.test`, `auditor@demo.test`, platform `admin@complymate.test`.

## Tests

```bash
make test        # ruff + mypy + pytest (unit, integration with Testcontainers, contract)
pnpm -r test     # Vitest
pnpm --filter web e2e   # Playwright
```

## Deploying to AWS

See [docs/architecture/aws.md](docs/architecture/aws.md). Short version:

1. Bootstrap the Terraform state bucket (`infra/terraform/global`).
2. Configure GitHub OIDC role (`AWS_DEPLOY_ROLE_ARN`) per account.
3. Push to `main` → `deploy-aws.yml` builds the image, pushes to ECR, runs `terraform apply` for `aws-dev`,
   then invokes the worker Lambda with `{"task": "migrate"}` and `{"task": "seed_reference"}`.

## Architecture rules

* Business logic never imports a cloud SDK. It calls ports in `complymate/ports`. Adapters live in `complymate/adapters/{aws,azure,local}`.
* Two locks on tenant data: an RBAC/ABAC check in a FastAPI dependency **and** PostgreSQL Row-Level Security.
* The audit log is append-only (INSERT/SELECT grants only) and hash-chained per tenant, with an immutable copy in S3 Object Lock.
* The risk engine is deterministic (YAML rules), never AI. AI outputs always show sources and a human decides.
