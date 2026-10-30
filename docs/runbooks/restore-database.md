# Runbook: restore the database

Targets: RPO 15 minutes, RTO 4 hours.

## Point-in-time restore (AWS)

```bash
aws rds restore-db-cluster-to-point-in-time \
  --source-db-cluster-identifier complymate-prod \
  --db-cluster-identifier complymate-prod-restore-$(date +%Y%m%d%H%M) \
  --restore-to-time 2026-10-30T03:15:00Z \
  --db-subnet-group-name complymate-prod --vpc-security-group-ids <db-sg> \
  --kms-key-id <data-key-arn> --serverless-v2-scaling-configuration MinCapacity=1,MaxCapacity=32
aws rds create-db-instance --db-instance-identifier <restore>-0 --db-cluster-identifier <restore> \
  --engine aurora-postgresql --db-instance-class db.serverless
```

1. Restore to a **new** cluster; never overwrite the original.
2. Verify: row counts, latest audit events, and run `verify_audit_chain` against the restored cluster.
3. Point RDS Proxy target (or `DB_ADMIN_HOST`/secret host) at the restored cluster via Terraform (import, then
   rename) or a temporary change, then redeploy Lambdas.
4. Re-run any audit archive batches after the restore point (the S3 Object Lock copy holds everything archived).

## From AWS Backup (incl. Melbourne copy)
Use the AWS Backup console → recovery point in `complymate-prod-primary` or `complymate-prod-dr` → Restore.

## Azure
`az postgres flexible-server restore --source-server complymate-prod-pg --restore-time <UTC> --name <new>`
(geo-restore from the paired region with `geo-restore` if the region is unavailable).
