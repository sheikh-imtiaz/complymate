# AWS deployment (ap-southeast-2)

All tenant data stays in Australia. DR backup copies go to Melbourne (ap-southeast-4).

## Components

* **Edge**: Route 53, CloudFront + AWS WAF (managed rule sets, rate limit) for `api.<domain>`; Amplify Hosting for
  `app.<domain>` and `admin.<domain>`.
* **Identity**: Cognito user pool, MFA required (TOTP), two app clients (tenant web, platform admin).
* **API**: API Gateway HTTP API with a Cognito JWT authorizer → Lambda (container image, `api_handler`).
* **Chat streaming**: API Gateway WebSocket → Lambda (`ws_handler`), tokens pushed with `@connections`.
* **Workers**: SQS queues (+DLQs) → Lambda (`worker_handler`, partial batch failures); EventBridge Scheduler for
  nightly jobs; Step Functions for program drafting (Map over sections) and the regulator pack.
* **AI**: Bedrock (Claude Sonnet/Haiku via AU inference profiles, Titan Embeddings v2), Bedrock Guardrails, Textract.
* **Data**: Aurora PostgreSQL Serverless v2 + pgvector behind RDS Proxy; S3 (documents, exports, Object Lock
  audit archive) with KMS; Secrets Manager.
* **Ops**: CloudWatch logs (30 days), X-Ray, EMF metrics, alarms → SNS, dashboard, AWS Budgets.

## First deployment

```bash
# 1. Bootstrap each account (state bucket, lock table, ECR, GitHub OIDC role)
cd infra/terraform/global
terraform init && terraform apply -var account_name=dev -var github_repo=<owner>/complymate

# 2. In GitHub: environment "dev" with secrets AWS_DEPLOY_ROLE_ARN (output deploy_role_arn) and
#    AMPLIFY_GITHUB_TOKEN (fine-grained token, repo read). Enable Bedrock model access in the console.

# 3. Push to main → .github/workflows/deploy-aws.yml builds the image, applies envs/aws-dev, runs
#    {"task":"migrate"} and {"task":"seed_reference"} on the worker Lambda and smoke-tests /health.

# 4. Set the Stripe secret value (output stripe_secret_arn) and create the first platform admin:
aws lambda invoke --function-name complymate-dev-worker \
  --payload '{"task":"migrate"}' --cli-binary-format raw-in-base64-out /dev/stdout
```

Without a domain (`zone_name = null`) the API is served from the CloudFront default domain and the apps from the
Amplify default domains; after the first apply put those URLs in `web_url`/`admin_url` in `terraform.tfvars`
(they are used for Cognito callbacks and CORS) and apply again.

## Sizing

| | dev | staging | prod |
|---|---|---|---|
| Aurora ACU | 0–4 (auto-pause) | 0.5–8 | 1–32, writer + reader |
| API provisioned concurrency | 0 | 0 | 2 |
| AZs | 2 | 2 | 3 |
| NAT | 1 | 1 | 1 |

Egress: the Lambdas need the internet for Stripe and sanctions-list downloads, so one NAT gateway is created.
VPC endpoints (S3 gateway; Secrets Manager, SQS, KMS, Bedrock interface) keep AWS traffic private and cheap. Set
`enable_nat_gateway = false` to go endpoint-only (then run list refresh and Stripe calls outside the VPC).

## Backups and recovery

Aurora PITR 35 days (RPO ≤ 15 min target), daily AWS Backup with a copy to Melbourne, S3 versioning.
See [runbooks/restore-database.md](../runbooks/restore-database.md). RTO target 4 hours.
