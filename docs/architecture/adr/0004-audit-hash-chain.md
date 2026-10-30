# ADR 0004: Append-only, hash-chained audit log with an immutable copy

* Status: accepted
* Date: 2026-10-30

## Context
Regulators expect a reliable record of who did what. A database table alone can be altered by anyone with
sufficient access.

## Decision
* `audit_events` is append-only: the app role has `INSERT, SELECT` only, and a trigger blocks `UPDATE`/`DELETE`/
  `TRUNCATE` even for the owner.
* Each event stores `prev_hash` and `hash = SHA-256(prev_hash || canonical_json(event))`, per tenant (platform
  events form their own chain). Writers take a per-tenant advisory lock so the chain stays linear.
* A nightly job verifies every chain; a break raises the `AuditChainBreak` alarm.
* Every 15 minutes new events are copied to S3 Object Lock (compliance mode, 7 years) / Blob locked immutability.
* AI actions record model, prompt version, sources, tool calls and the user's decision.

## Consequences
Tampering with the database is detectable, and the immutable copy allows reconstruction. See the
[audit chain break runbook](../../runbooks/audit-chain-break.md).
