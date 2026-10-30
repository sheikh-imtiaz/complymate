"""Application settings. Values come from environment variables (12-factor).

Cloud-specific values are optional; the container only reads the ones for the selected CLOUD_PROVIDER.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PACKAGE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "local"
    cloud_provider: Literal["local", "aws", "azure"] = "local"
    log_level: str = "INFO"
    service_name: str = "complymate-api"
    default_jurisdiction: Literal["AU", "NZ"] = "AU"
    run_mode: Literal["api", "worker"] = "api"

    # Database. On AWS/Azure the URL is built from a secret (DB_SECRET_ARN / key vault name).
    database_url: str | None = None
    database_admin_url: str | None = None
    app_db_password: str | None = None
    db_secret_arn: str | None = None
    db_admin_secret_arn: str | None = None
    db_pool_size: int = 5
    db_max_overflow: int = 5

    # Auth
    dev_jwt_secret: str = "change-me-dev-only"  # noqa: S105 - dev only
    oidc_issuer: str | None = None
    oidc_audience: str | None = None
    oidc_jwks_url: str | None = None
    cognito_user_pool_id: str | None = None
    step_up_mfa_seconds: int = 600
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000", "http://localhost:3001"])
    web_base_url: str = "http://localhost:3000"
    admin_base_url: str = "http://localhost:3001"

    # AWS
    aws_region: str = "ap-southeast-2"
    documents_bucket: str = "complymate-documents"
    exports_bucket: str = "complymate-exports"
    audit_archive_bucket: str = "complymate-audit"
    kms_key_id: str | None = None
    queue_url_prefix: str | None = None
    ws_api_endpoint: str | None = None
    state_machine_program_draft_arn: str | None = None
    state_machine_regulator_pack_arn: str | None = None
    scheduler_group: str = "complymate"
    scheduler_role_arn: str | None = None
    scheduler_target_queue_arn: str | None = None
    ses_configuration_set: str | None = None
    stripe_secret_arn: str | None = None

    # Local stack
    s3_endpoint_url: str | None = None
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    audit_sink_dir: str = ".data/audit-archive"

    # Azure
    azure_storage_account_url: str | None = None
    azure_servicebus_namespace: str | None = None
    azure_key_vault_url: str | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_version: str = "2024-10-21"
    azure_foundry_endpoint: str | None = None
    azure_docintel_endpoint: str | None = None
    azure_acs_endpoint: str | None = None
    azure_subscription_id: str | None = None
    azure_resource_group: str | None = None
    azure_jobs_environment: str | None = None
    azure_audit_container: str = "audit"

    # Email
    email_from: str = "no-reply@complymate.test"
    security_alert_email: str | None = None

    # AI
    llm_model_id: str = "anthropic.claude-sonnet-4-5"
    llm_fast_model_id: str = "anthropic.claude-haiku-4-5"
    embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    embedding_dimensions: int = 1024
    bedrock_guardrail_id: str | None = None
    bedrock_guardrail_version: str | None = None
    llm_input_cost_per_mtok: float = 3.0
    llm_output_cost_per_mtok: float = 15.0
    llm_monthly_budget_usd: float = 500.0
    prompt_version: str = "2026-10-01"

    # Billing
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_solo: str | None = None
    stripe_price_practice: str | None = None
    stripe_price_onboarding: str | None = None

    # Uploads
    max_upload_bytes: int = 5 * 1024 * 1024

    # Telemetry
    otel_exporter_otlp_endpoint: str | None = None

    templates_dir: str = str(PACKAGE_DIR.parent.parent / "templates")
    rules_dir: str = str(PACKAGE_DIR / "rules")

    @property
    def is_local(self) -> bool:
        return self.cloud_provider == "local"


@lru_cache
def get_settings() -> Settings:
    return Settings()
