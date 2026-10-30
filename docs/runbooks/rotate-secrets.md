# Runbook: rotate secrets

| Secret | Where | How |
|---|---|---|
| Aurora master | Secrets Manager (RDS-managed) | Rotate in RDS console or `aws secretsmanager rotate-secret`; RDS Proxy picks it up |
| App DB password | `complymate-<env>/db-app` | Taint `random_password.app` → `terraform apply`, then invoke `{"task":"migrate"}` (0001 sets the role password from the secret) |
| Stripe keys | `complymate-<env>/stripe` | Roll in Stripe dashboard, update the JSON secret; Lambdas re-read within 5 minutes |
| Cognito app clients | Terraform | Public clients have no secret; to revoke sessions use global sign-out |
| API keys (tenant) | DB (hash only) | Firm admin → API keys → Revoke, then create a new one |
| KMS data key | KMS | Automatic yearly rotation; tenant data keys stay decryptable |
| Azure | Key Vault | Update the secret version; managed identities need no change |

After any rotation: check CloudWatch for auth errors for 15 minutes and record the rotation in the platform audit
log (Platform Admin → note in system health) or the change ticket.
