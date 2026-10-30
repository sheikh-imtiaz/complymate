"""Dependency container: picks adapters from CLOUD_PROVIDER. The only module that imports adapters."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from complymate.config import Settings, get_settings
from complymate.ports.audit_sink import AuditSink
from complymate.ports.email import EmailSender
from complymate.ports.embeddings import EmbeddingProvider
from complymate.ports.identity import IdentityProvider
from complymate.ports.kms import KeyManagement
from complymate.ports.llm import LLMProvider
from complymate.ports.ocr import DocumentOCR
from complymate.ports.queue import Queue, WorkflowStarter
from complymate.ports.realtime import RealtimePusher
from complymate.ports.scheduler import Scheduler
from complymate.ports.secrets import SecretStore
from complymate.ports.storage import ObjectStorage


@dataclass
class Container:
    settings: Settings
    llm: LLMProvider
    embeddings: EmbeddingProvider
    storage: ObjectStorage
    queue: Queue
    workflows: WorkflowStarter
    scheduler: Scheduler
    email: EmailSender
    ocr: DocumentOCR
    secrets: SecretStore
    kms: KeyManagement
    identity: IdentityProvider
    audit_sink: AuditSink
    realtime: RealtimePusher
    _engine: AsyncEngine | None = None
    _sessionmaker: async_sessionmaker[AsyncSession] | None = None
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def database_url(self, admin: bool = False) -> str:
        s = self.settings
        url = s.database_admin_url if admin else s.database_url
        if url:
            return url
        secret_name = s.db_admin_secret_arn if admin else s.db_secret_arn
        if not secret_name:
            raise RuntimeError("DATABASE_URL or DB_SECRET_ARN must be set")
        sec = await self.secrets.get_json(secret_name)
        host = sec.get("proxy_host") or sec.get("host") or (s.db_admin_host if admin else s.db_host)
        if not host:
            raise RuntimeError("database host missing from secret and DB_HOST/DB_ADMIN_HOST")
        return (
            f"postgresql+asyncpg://{quote_plus(sec['username'])}:{quote_plus(sec['password'])}"
            f"@{host}:{sec.get('port', s.db_port)}/{sec.get('dbname', s.db_name)}"
        )

    async def sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        if self._sessionmaker is None:
            async with self._lock:
                if self._sessionmaker is None:
                    connect_args: dict[str, Any] = {"server_settings": {"application_name": self.settings.service_name}}
                    if self.settings.cloud_provider != "local":
                        connect_args["ssl"] = "require"
                    # RDS Proxy multiplexes connections; keep the Lambda-side pool small.
                    self._engine = create_async_engine(
                        await self.database_url(),
                        pool_size=self.settings.db_pool_size,
                        max_overflow=self.settings.db_max_overflow,
                        pool_pre_ping=True,
                        pool_recycle=300,
                        connect_args=connect_args,
                    )
                    self._sessionmaker = async_sessionmaker(self._engine, expire_on_commit=False)
        return self._sessionmaker

    async def dispose(self) -> None:
        if self._engine is not None:
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None


def _build_local(s: Settings) -> Container:
    from complymate.adapters.local.cron_scheduler import CronScheduler
    from complymate.adapters.local.dev_identity import DevIdentity
    from complymate.adapters.local.env_secrets import EnvSecrets
    from complymate.adapters.local.fake_embeddings import FakeEmbeddings
    from complymate.adapters.local.fake_llm import FakeLLM
    from complymate.adapters.local.fake_ocr import FakeOCR
    from complymate.adapters.local.file_audit_sink import FileAuditSink
    from complymate.adapters.local.local_kms import LocalKMS
    from complymate.adapters.local.mailpit_email import MailpitEmail
    from complymate.adapters.local.memory_queue import InProcessWorkflows, MemoryQueue
    from complymate.adapters.local.minio_storage import MinioStorage
    from complymate.adapters.local.noop_realtime import NoopRealtime

    return Container(
        settings=s,
        llm=FakeLLM(),
        embeddings=FakeEmbeddings(s.embedding_dimensions),
        storage=MinioStorage(
            s.s3_endpoint_url or "http://localhost:9000",
            s.s3_access_key or "minioadmin",
            s.s3_secret_key or "minioadmin",
        ),
        queue=MemoryQueue(),
        workflows=InProcessWorkflows(),
        scheduler=CronScheduler(),
        email=MailpitEmail(s.smtp_host, s.smtp_port, s.email_from),
        ocr=FakeOCR(),
        secrets=EnvSecrets(),
        kms=LocalKMS(s.dev_jwt_secret),
        identity=DevIdentity(s.dev_jwt_secret),
        audit_sink=FileAuditSink(s.audit_sink_dir),
        realtime=NoopRealtime(),
    )


def _build_aws(s: Settings) -> Container:
    from complymate.adapters.aws.apigw_realtime import ApiGatewayRealtime
    from complymate.adapters.aws.bedrock_embeddings import BedrockEmbeddings
    from complymate.adapters.aws.bedrock_llm import BedrockLLM
    from complymate.adapters.aws.cognito_identity import CognitoIdentity
    from complymate.adapters.aws.eventbridge_scheduler import EventBridgeScheduler
    from complymate.adapters.aws.kms import AwsKMS
    from complymate.adapters.aws.s3_object_lock_sink import S3ObjectLockSink
    from complymate.adapters.aws.s3_storage import S3Storage
    from complymate.adapters.aws.secrets_manager import SecretsManagerStore
    from complymate.adapters.aws.ses_email import SesEmail
    from complymate.adapters.aws.sqs_queue import SqsQueue, StepFunctionsWorkflows
    from complymate.adapters.aws.textract_ocr import TextractOCR
    from complymate.adapters.local.noop_realtime import NoopRealtime

    r = s.aws_region
    return Container(
        settings=s,
        llm=BedrockLLM(r, s.llm_model_id, s.llm_fast_model_id, s.bedrock_guardrail_id, s.bedrock_guardrail_version),
        embeddings=BedrockEmbeddings(r, s.embedding_model_id, s.embedding_dimensions),
        storage=S3Storage(r, kms_key_id=s.kms_key_id),
        queue=SqsQueue(r, s.queue_url_prefix or ""),
        workflows=StepFunctionsWorkflows(
            r,
            {"program_draft": s.state_machine_program_draft_arn, "regulator_pack": s.state_machine_regulator_pack_arn},
        ),
        scheduler=EventBridgeScheduler(
            r, s.scheduler_group, s.scheduler_role_arn or "", s.scheduler_target_queue_arn or ""
        ),
        email=SesEmail(r, s.email_from, s.ses_configuration_set),
        ocr=TextractOCR(r),
        secrets=SecretsManagerStore(r),
        kms=AwsKMS(r, s.kms_key_id or "alias/complymate"),
        identity=CognitoIdentity(r, s.cognito_user_pool_id or "", s.oidc_audience or ""),
        audit_sink=S3ObjectLockSink(r, s.audit_archive_bucket, kms_key_id=s.kms_key_id),
        realtime=ApiGatewayRealtime(r, s.ws_api_endpoint) if s.ws_api_endpoint else NoopRealtime(),
    )


def _build_azure(s: Settings) -> Container:
    import os

    from complymate.adapters.azure.acs_email import AcsEmail
    from complymate.adapters.azure.blob_immutable_sink import BlobImmutableSink
    from complymate.adapters.azure.blob_storage import BlobStorage
    from complymate.adapters.azure.container_jobs_scheduler import ContainerJobsScheduler
    from complymate.adapters.azure.docintel_ocr import DocIntelOCR
    from complymate.adapters.azure.entra_identity import EntraIdentity
    from complymate.adapters.azure.foundry_llm import FoundryLLM
    from complymate.adapters.azure.key_vault_kms import KeyVaultKMS
    from complymate.adapters.azure.key_vault_secrets import KeyVaultSecrets
    from complymate.adapters.azure.openai_embeddings import AzureOpenAIEmbeddings
    from complymate.adapters.azure.servicebus_queue import DurableWorkflows, ServiceBusQueue
    from complymate.adapters.local.noop_realtime import NoopRealtime

    return Container(
        settings=s,
        llm=FoundryLLM(
            s.azure_foundry_endpoint or s.azure_openai_endpoint or "",
            s.llm_model_id,
            s.llm_fast_model_id,
            s.azure_openai_api_version,
        ),
        embeddings=AzureOpenAIEmbeddings(
            s.azure_openai_endpoint or "", s.embedding_model_id, s.azure_openai_api_version, s.embedding_dimensions
        ),
        storage=BlobStorage(s.azure_storage_account_url or ""),
        queue=ServiceBusQueue(s.azure_servicebus_namespace or ""),
        workflows=DurableWorkflows(os.environ.get("AZURE_DURABLE_URL", ""), os.environ.get("AZURE_DURABLE_KEY", "")),
        scheduler=ContainerJobsScheduler(
            s.azure_subscription_id or "",
            s.azure_resource_group or "",
            s.azure_jobs_environment or "",
            os.environ.get("WORKER_IMAGE", ""),
            os.environ.get("AZURE_LOCATION", "australiaeast"),
        ),
        email=AcsEmail(s.azure_acs_endpoint or "", s.email_from),
        ocr=DocIntelOCR(s.azure_docintel_endpoint or ""),
        secrets=KeyVaultSecrets(s.azure_key_vault_url or ""),
        kms=KeyVaultKMS(s.azure_key_vault_url or "", "documents"),
        identity=EntraIdentity(s.oidc_issuer or "", s.oidc_audience or "", s.oidc_jwks_url),
        audit_sink=BlobImmutableSink(s.azure_storage_account_url or "", s.azure_audit_container),
        realtime=NoopRealtime(),
    )


_container: Container | None = None


def build_container(settings: Settings | None = None) -> Container:
    s = settings or get_settings()
    builders = {"local": _build_local, "aws": _build_aws, "azure": _build_azure}
    return builders[s.cloud_provider](s)


def get_container() -> Container:
    global _container
    if _container is None:
        _container = build_container()
    return _container


def set_container(container: Container | None) -> None:
    """Tests swap in a container with fakes."""
    global _container
    _container = container
