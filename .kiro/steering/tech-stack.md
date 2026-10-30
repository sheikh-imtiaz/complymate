---
inclusion: always
---
# Tech stack

* Backend: Python 3.12, FastAPI + Pydantic v2, SQLAlchemy 2 async + Alembic, PostgreSQL 16 + pgvector, uv.
* Agent: Strands Agents SDK; model via the `LLMProvider` port (Bedrock Claude on AWS, Azure AI Foundry on Azure).
* Frontend: Next.js 15 App Router, React 19, TypeScript 5, Tailwind CSS 4, shadcn-style components in
  `packages/ui`, TanStack Query/Table, React Hook Form + Zod, Tiptap, Recharts, oidc-client-ts, next-intl.
* Tests: pytest (+Testcontainers/real Postgres), moto, Vitest + Testing Library, Playwright.
* Infra: Terraform 1.9 (`infra/terraform/modules/{aws,azure}`), GitHub Actions with OIDC.
* Monorepo: pnpm workspaces (frontend), uv (Python). Run `make help`-style targets from the root Makefile.
