---
inclusion: always
---
# Cloud portability

* Business logic calls ports (`complymate/ports`). Only `container.py` imports adapters.
* A feature that needs a new cloud service gets a new port + AWS, Azure and local adapters + a contract test.
* Use PostgreSQL features available on both Aurora and Azure Flexible Server (pgvector, pg_trgm, pgcrypto, RLS).
* Configuration via environment variables only (`config.py`); Terraform sets them per cloud.
* Keep `CLOUD_PROVIDER=local` working for every feature so tests and onboarding never need a cloud account.
