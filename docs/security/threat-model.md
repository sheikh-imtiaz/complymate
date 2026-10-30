# Threat model (STRIDE summary)

Assets: client identity data and documents, SMRs, AML/CTF programs, audit log, credentials, LLM spend.

| Threat | Example | Controls |
|---|---|---|
| **Spoofing** | Stolen password | Cognito/Entra MFA required; step-up MFA for sensitive actions; short ID tokens; token revocation on deactivate |
| | Forged JWT | Signature + issuer + audience verified in API Gateway *and* the app (JWKS) |
| **Tampering** | Edit audit history | INSERT/SELECT grants only + trigger; per-tenant hash chain; nightly verification; Object Lock copy |
| | Change a high-risk decision alone | Four-eyes checks for client approval and program sign-off |
| **Repudiation** | "I didn't approve that" | Audit events with actor, role, IP, request id, before/after |
| **Information disclosure** | Cross-tenant data via a buggy query | RLS on every tenant table (second lock), tenant header checked against memberships |
| | Support staff reading documents | RLS has no platform bypass on documents/parties/SMRs; impersonation needs consent + expiry |
| | PII in logs | structlog PII filter; no request bodies logged |
| | Prompt injection exfiltrating data | Agent tools run in the caller's RLS session and re-check permissions; output guardrails redact IDs |
| | Document theft from storage | Per-tenant data keys (envelope encryption) + SSE-KMS, private buckets, TLS-only policies |
| **Denial of service** | Request floods | WAF rate rules, API Gateway throttling, in-app token bucket; queue-based workers |
| | LLM cost abuse | Plan limits on agent turns, per-tenant usage metering, budget alarms |
| **Elevation of privilege** | Staff grants themselves Owner | Only owners grant owner; role changes audited + step-up; API keys cannot approve or manage users |
| | Tipping-off via AI | Input/output guardrails + Bedrock denied topic; SMR access limited to SMR roles |

Residual risks and follow-ups: independent pen test before first large customer (ASVS L2), WebAuthn passkeys,
signed container images, VPC endpoint-only egress for prod.
