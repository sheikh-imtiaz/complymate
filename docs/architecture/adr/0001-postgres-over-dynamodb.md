# ADR 0001: PostgreSQL 16 instead of DynamoDB

* Status: accepted
* Date: 2026-10-30

## Context
The earlier roadmap used DynamoDB. We need to run on Azure later, our data is relational (clients, parties,
assessments, approvals), and tenant isolation must be provable to regulators and auditors.

## Decision
Use PostgreSQL 16: Aurora Serverless v2 on AWS, Azure Database for PostgreSQL Flexible Server on Azure.
Isolate tenants with Row-Level Security keyed on `app.tenant_id`, set per transaction.

## Consequences
* Same schema, migrations (Alembic) and SQL on both clouds.
* Two locks: API permission checks and RLS. An app bug that forgets a filter cannot leak data across tenants.
* Lambda needs RDS Proxy to avoid connection storms; Serverless v2 can scale to zero in dev.
* The app role is not the table owner and has no BYPASSRLS; migrations run as the owner role.
