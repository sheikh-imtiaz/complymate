# Azure target (Australia East; New Zealand North for NZ residency where required)

Same container image and code with `CLOUD_PROVIDER=azure`. Terraform: `infra/terraform/envs/azure-{staging,prod}`.

| AWS | Azure |
|---|---|
| CloudFront + WAF | Front Door Premium + WAF policy |
| Amplify Hosting | Container Apps (Next.js standalone images) |
| Cognito | Entra External ID (app registrations via `azuread`) |
| API Gateway + Lambda | Container Apps (uvicorn), native WebSocket for `/ws/chat` |
| SQS / Lambda workers | Service Bus / worker Container App (`worker`) |
| EventBridge Scheduler / Step Functions | Container Apps Jobs (cron) / Durable Functions (optional) |
| Bedrock / Guardrails | Azure AI Foundry (Claude) or Azure OpenAI / AI Content Safety |
| Textract | AI Document Intelligence (`prebuilt-idDocument`) |
| Aurora PostgreSQL + pgvector | PostgreSQL Flexible Server 16 + `VECTOR` extension |
| S3 / Object Lock | Blob Storage / locked time-based immutability policy |
| Secrets Manager / KMS | Key Vault (secrets, RSA-HSM wrapping key) |
| CloudWatch / X-Ray | Log Analytics + Application Insights |
| SES | Communication Services Email |

## Notes

* **Identity**: create the Entra External ID tenant in the portal, enable a sign-up/sign-in user flow and a
  Conditional Access policy requiring MFA. Terraform creates the two SPA app registrations in that tenant.
  The API reads `auth_time` and `amr` claims for step-up.
* **No keys**: Container Apps use a user-assigned managed identity with data-plane roles (Blob Data Contributor,
  Key Vault Secrets/Crypto User, Service Bus Sender/Receiver, OpenAI User). Storage shared keys are disabled.
* **Regulatory**: check which Claude / OpenAI models and Document Intelligence features are offered in the region
  before promising data residency.
* **Migrations**: run the image with `migrate` as a one-off Container Apps job (deploy-azure.yml does this).
