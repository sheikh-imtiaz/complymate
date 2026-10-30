# Architecture overview

ComplyMate is a multi-tenant AML/CTF compliance SaaS for small firms (AU Tranche 2 first, then NZ AML/CFT).

## Building blocks

| Layer | What | Where |
|---|---|---|
| Web apps | Next.js 15 tenant app + separate platform admin app | `apps/web`, `apps/platform-admin` |
| API | FastAPI (Python 3.12), one container image | `services/api` |
| Workers | Same image; queue/schedule/workflow entrypoints | `services/api/src/complymate/workers` |
| Agent | Strands Agents (model-agnostic), RAG on pgvector, guardrails | `services/api/src/complymate/agent` |
| Data | PostgreSQL 16 + pgvector, Row-Level Security | Aurora Serverless v2 / Azure Flexible Server |
| Files | Encrypted documents, exports, immutable audit archive | S3 (+Object Lock) / Blob (+immutability) |
| IaC | Terraform (OpenTofu compatible), AWS and Azure modules | `infra/terraform` |

## Request path

1. The browser signs in with OIDC (Cognito / Entra External ID), MFA required.
2. Calls go to the API with the ID token and `X-Tenant-Id`.
3. `api/deps.py` verifies the token, loads the membership and role permissions, and opens **one transaction**
   with `set_config('app.tenant_id', …)` so PostgreSQL RLS filters every query.
4. The route's `require(permission)` dependency checks RBAC/ABAC (own/shared scope, step-up MFA).
5. Business changes call `ctx.record(...)`, which appends a hash-chained audit event in the same transaction.

## Key decisions

* [ADR 0001](adr/0001-postgres-over-dynamodb.md) — PostgreSQL instead of DynamoDB (portability, RLS).
* [ADR 0002](adr/0002-pgvector-for-rag.md) — pgvector in the same database for RAG.
* [ADR 0003](adr/0003-terraform-over-cdk.md) — Terraform for both clouds.
* [ADR 0004](adr/0004-audit-hash-chain.md) — append-only hash-chained audit log + immutable copy.

Diagrams: [user flow](diagrams/user-flow.mmd), [agent flow](diagrams/agent-flow.mmd), [AWS](diagrams/aws.mmd),
[Azure](diagrams/azure.mmd). See [ports-and-adapters.md](ports-and-adapters.md) for the cloud abstraction.

## Deviations from the original design document (and why)

* **Lambda runtime**: the image uses the Lambda Runtime Interface Client with Mangum (one image, three handlers:
  API, worker, WebSocket) instead of the Lambda Web Adapter, because the same image must also serve API Gateway
  WebSocket events and SQS batches. Azure runs the identical image with uvicorn.
* **WAF placement**: CloudFront + WAF sits in front of the HTTP API (`api.<domain>`); Amplify Hosting serves the
  Next.js apps on its own managed CloudFront.
* **API keys**: machine clients call `/m2m/*` (no JWT authorizer at API Gateway; the app requires `X-API-Key`).
* **Composition modules**: `infra/terraform/modules/{aws,azure}/stack` compose the per-service modules so the
  env folders stay small; a `frontend` module (Amplify) was added on AWS.
