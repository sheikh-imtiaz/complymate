# Ports and adapters

**Rule: business logic never imports a cloud SDK.** Domain code (`complymate/domain`) is pure Python. Application
services (`complymate/application`) and workers call *ports* (`complymate/ports`). `complymate/container.py` is the
only place that imports adapters and picks them from `CLOUD_PROVIDER=aws|azure|local`.

| Port | AWS adapter | Azure adapter | Local adapter |
|---|---|---|---|
| `LLMProvider` | `aws/bedrock_llm.py` (Converse + Guardrails, Strands `BedrockModel`) | `azure/foundry_llm.py` (OpenAI-compatible) | `local/fake_llm.py` |
| `EmbeddingProvider` | `aws/bedrock_embeddings.py` (Titan v2, 1024 dims) | `azure/openai_embeddings.py` (3-small @1024) | `local/fake_embeddings.py` |
| `ObjectStorage` | `aws/s3_storage.py` | `azure/blob_storage.py` | `local/minio_storage.py` |
| `Queue`, `WorkflowStarter` | `aws/sqs_queue.py` (SQS, Step Functions) | `azure/servicebus_queue.py` | `local/memory_queue.py` |
| `Scheduler` | `aws/eventbridge_scheduler.py` | `azure/container_jobs_scheduler.py` | `local/cron_scheduler.py` |
| `EmailSender` | `aws/ses_email.py` | `azure/acs_email.py` | `local/mailpit_email.py` |
| `DocumentOCR` | `aws/textract_ocr.py` | `azure/docintel_ocr.py` | `local/fake_ocr.py` |
| `SecretStore` | `aws/secrets_manager.py` | `azure/key_vault_secrets.py` | `local/env_secrets.py` |
| `KeyManagement` | `aws/kms.py` | `azure/key_vault_kms.py` | `local/local_kms.py` |
| `IdentityProvider` | `aws/cognito_identity.py` | `azure/entra_identity.py` | `local/dev_identity.py` |
| `AuditSink` | `aws/s3_object_lock_sink.py` | `azure/blob_immutable_sink.py` | `local/file_audit_sink.py` |
| `RealtimePusher` | `aws/apigw_realtime.py` | native WebSocket (no-op) | no-op |

`tests/contract/test_adapters.py` runs the same contract against each adapter (AWS via moto; Azure in the nightly
Azure job with `CONTRACT_AZURE=1`).

## Adding a port

1. Define a `Protocol` in `ports/`.
2. Implement `adapters/{aws,azure,local}/…`.
3. Wire it in `container.py` (all three builders).
4. Add a contract test.
