# Incident response

## Severity

| Sev | Examples | Response |
|---|---|---|
| 1 | Cross-tenant data exposure, audit chain break, credential leak, production down | Page on-call immediately; founders informed within 30 min |
| 2 | Partial outage, failed nightly screening, DLQ growth, suspicious login spike | Respond within 2 hours |
| 3 | Single-user issue, non-sensitive bug | Next business day |

## Steps

1. **Detect** — CloudWatch/Azure alerts (SNS/action group), security_event spikes, customer report.
2. **Contain** — revoke sessions (`identity.sign_out_everywhere`), disable API keys, suspend tenant
   (`POST /platform/tenants/{id}/suspend`), block IPs in WAF, rotate secrets ([runbook](../runbooks/rotate-secrets.md)).
3. **Preserve evidence** — snapshot Aurora, keep CloudTrail/CloudWatch logs, export audit chain; never modify
   `audit_events` (it is append-only and Object-Locked).
4. **Eradicate and recover** — fix, redeploy through CI, restore data if needed ([runbook](../runbooks/restore-database.md)).
5. **Notify** — eligible data breaches: notify affected customers and the OAIC under the Notifiable Data Breaches
   scheme (AU) / the Privacy Commissioner (NZ) as soon as practicable. Customers decide on their own regulator
   notifications.
6. **Review** — blameless post-incident review within 5 business days; track actions.
