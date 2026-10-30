# Runbook: audit chain break (alarm `AuditChainBreak`)

The nightly `verify_audit_chain` job found an event whose `prev_hash` or `hash` doesn't match. Treat as **Sev 1**
until proven otherwise.

1. **Identify** — Platform Admin → System health shows the tenant and `broken_at_id`. Or:
   `SELECT * FROM audit_chain_verifications WHERE NOT ok ORDER BY checked_at DESC;`
2. **Freeze** — do not run migrations or manual SQL. Snapshot the database.
3. **Compare with the immutable copy** — download the tenant's batches from the audit bucket
   (`s3://complymate-<env>-audit-<acct>/<tenant>/…jsonl`, Object Lock) and diff the event at `broken_at_id`.
4. **Classify**
   * *Content differs from the archive* → tampering. Start incident response, check CloudTrail/DB logs for the
     session that changed it (UPDATE should be impossible — the trigger raises — so look for owner-role abuse,
     trigger removal or restore from an altered snapshot).
   * *Event missing from DB but present in archive* → deletion; same as above.
   * *Event not yet archived and no other evidence* → check for a deployment that changed hashing/canonical JSON.
5. **Recover** — the archive is the source of truth. Restore from a clean snapshot or re-insert from the archive
   into a new table for investigation; never edit history in place.
6. **Notify** the affected firm's owner and AMLCO with what happened and the integrity evidence.
