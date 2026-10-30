# Data classification

| Class | Examples | Storage | Access | Retention |
|---|---|---|---|---|
| **Restricted** | ID documents, OCR fields, SMR cases/notes, beneficial owner details, DOBs | Encrypted (tenant data key + KMS); RLS strict (no platform access) | Need-to-know roles; download audited (`view_sensitive`) | ≥ 7 years after relationship ends |
| **Confidential** | Client records, risk assessments, screening results, programs, audit log | PostgreSQL (encrypted at rest), RLS | Tenant roles per matrix | ≥ 7 years |
| **Internal** | Usage counters, LLM call metrics, feature flags | PostgreSQL | Platform staff | 2 years |
| **Public** | Rule library summaries, designated services questions | PostgreSQL | Everyone | Until superseded |

Rules:

* Restricted and Confidential data never goes into system logs, metrics dimensions, tags or error messages.
* Exports are generated on request, stored 30 days in the exports bucket, downloaded via 5-minute signed URLs.
* LLM prompts contain rule-library sources and the user's question; client data only via permission-checked tools.
* Data stays in AU (ap-southeast-2 / Australia East); DR copies in Melbourne / Australia Southeast.
