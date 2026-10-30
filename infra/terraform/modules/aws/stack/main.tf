# Composition root for one AWS environment (dev / staging / prod). envs/aws-* call this with sizing variables.
terraform {
  required_providers {
    aws = {
      source                = "hashicorp/aws"
      version               = "~> 5.80"
      configuration_aliases = [aws.us_east_1, aws.dr]
    }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

locals {
  name       = "complymate-${var.environment}"
  account    = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.name
  has_domain = var.zone_name != null
  api_domain = local.has_domain ? "api.${var.zone_name}" : null
  web_url    = local.has_domain ? "https://app.${var.zone_name}" : var.web_url
  admin_url  = local.has_domain ? "https://admin.${var.zone_name}" : var.admin_url
  email_from = var.email_from != null ? var.email_from : (local.has_domain ? "no-reply@${var.zone_name}" : "no-reply@example.com")
  api_url    = local.has_domain ? "https://${local.api_domain}" : "https://${module.waf.distribution_domain}"
}

module "network" {
  source             = "../network"
  name               = local.name
  region             = local.region
  cidr               = var.vpc_cidr
  az_count           = var.az_count
  enable_nat_gateway = var.enable_nat_gateway
  endpoint_services  = var.endpoint_services
}

module "storage" {
  source          = "../storage"
  name            = local.name
  force_destroy   = var.environment == "dev"
  allowed_origins = [local.web_url, local.admin_url]
}

module "database" {
  source                    = "../database"
  providers                 = { aws = aws, aws.dr = aws.dr }
  name                      = local.name
  vpc_id                    = module.network.vpc_id
  vpc_cidr                  = module.network.vpc_cidr
  subnet_ids                = module.network.private_subnet_ids
  client_security_group_ids = [module.network.lambda_security_group_id]
  kms_key_arn               = module.storage.kms_key_arn
  min_acu                   = var.db_min_acu
  max_acu                   = var.db_max_acu
  instance_count            = var.db_instance_count
  deletion_protection       = var.environment != "dev"
}

module "dns" {
  count              = local.has_domain ? 1 : 0
  source             = "../dns"
  providers          = { aws = aws, aws.us_east_1 = aws.us_east_1 }
  name               = local.name
  zone_name          = var.zone_name
  api_domain         = local.api_domain
  email_domain       = var.zone_name
  cloudfront_domain  = module.waf.distribution_domain
  cloudfront_zone_id = module.waf.distribution_zone_id
}

module "identity" {
  source              = "../identity"
  name                = local.name
  domain_prefix       = "${local.name}-${substr(local.account, 0, 6)}"
  web_callback_urls   = distinct(concat(["${local.web_url}/callback"], var.extra_web_urls, var.environment == "dev" ? ["http://localhost:3000/callback"] : []))
  web_logout_urls     = distinct(concat(["${local.web_url}/sign-in"], var.environment == "dev" ? ["http://localhost:3000/sign-in"] : []))
  admin_callback_urls = distinct(concat(["${local.admin_url}/callback"], var.environment == "dev" ? ["http://localhost:3001/callback"] : []))
  admin_logout_urls   = distinct(concat(["${local.admin_url}/sign-in"], var.environment == "dev" ? ["http://localhost:3001/sign-in"] : []))
  deletion_protection = var.environment != "dev"
  advanced_security   = var.environment == "prod"
  ses_identity_arn    = local.has_domain ? module.dns[0].ses_identity_arn : null
  email_from          = local.has_domain ? local.email_from : null
}

module "ai" {
  source = "../ai"
  name   = local.name
}

resource "aws_secretsmanager_secret" "stripe" {
  name                    = "${local.name}/stripe"
  description             = "JSON: {\"secret_key\": \"sk_...\", \"webhook_secret\": \"whsec_...\"} — set the value manually"
  kms_key_id              = module.storage.kms_key_arn
  recovery_window_in_days = var.environment == "dev" ? 0 : 30
}

locals {
  queue_prefix = "https://sqs.${local.region}.amazonaws.com/${local.account}/${local.name}-"
  app_env = {
    ENVIRONMENT          = var.environment
    CLOUD_PROVIDER       = "aws"
    LOG_LEVEL            = var.environment == "prod" ? "INFO" : "DEBUG"
    DEFAULT_JURISDICTION = "AU"
    DB_SECRET_ARN        = module.database.app_secret_arn
    DB_ADMIN_SECRET_ARN  = module.database.master_secret_arn
    DB_HOST              = module.database.proxy_endpoint
    DB_ADMIN_HOST        = module.database.cluster_endpoint
    DOCUMENTS_BUCKET     = module.storage.documents_bucket
    EXPORTS_BUCKET       = module.storage.exports_bucket
    AUDIT_ARCHIVE_BUCKET = module.storage.audit_bucket
    KMS_KEY_ID           = module.storage.kms_key_arn
    QUEUE_URL_PREFIX     = local.queue_prefix
    # Built as strings (not module outputs) to avoid a cycle: workers ↔ Step Functions.
    STATE_MACHINE_PROGRAM_DRAFT_ARN  = "arn:aws:states:${local.region}:${local.account}:stateMachine:${local.name}-program-draft"
    STATE_MACHINE_REGULATOR_PACK_ARN = "arn:aws:states:${local.region}:${local.account}:stateMachine:${local.name}-regulator-pack"
    SCHEDULER_GROUP                  = local.name
    SCHEDULER_ROLE_ARN               = "arn:aws:iam::${local.account}:role/${local.name}-scheduler"
    SCHEDULER_TARGET_QUEUE_ARN       = "arn:aws:sqs:${local.region}:${local.account}:${local.name}-notifications"
    COGNITO_USER_POOL_ID             = module.identity.user_pool_id
    OIDC_ISSUER                      = module.identity.issuer
    OIDC_AUDIENCE                    = "${module.identity.web_client_id},${module.identity.admin_client_id}"
    WEB_BASE_URL                     = local.web_url
    ADMIN_BASE_URL                   = local.admin_url
    CORS_ORIGINS                     = jsonencode(distinct(concat([local.web_url, local.admin_url], var.extra_web_urls)))
    EMAIL_FROM                       = local.email_from
    SES_CONFIGURATION_SET            = local.has_domain ? module.dns[0].ses_configuration_set : ""
    LLM_MODEL_ID                     = var.llm_model_id
    LLM_FAST_MODEL_ID                = var.llm_fast_model_id
    EMBEDDING_MODEL_ID               = "amazon.titan-embed-text-v2:0"
    BEDROCK_GUARDRAIL_ID             = module.ai.guardrail_id
    BEDROCK_GUARDRAIL_VERSION        = module.ai.guardrail_version
    LLM_MONTHLY_BUDGET_USD           = tostring(var.llm_monthly_budget_usd)
    STRIPE_SECRET_ARN                = aws_secretsmanager_secret.stripe.arn
    STRIPE_PRICE_SOLO                = var.stripe_price_solo
    STRIPE_PRICE_PRACTICE            = var.stripe_price_practice
    STRIPE_PRICE_ONBOARDING          = var.stripe_price_onboarding
    DB_POOL_SIZE                     = "2"
    DB_MAX_OVERFLOW                  = "2"
  }
}

module "api" {
  source                  = "../api"
  name                    = local.name
  image_uri               = var.image_uri
  subnet_ids              = module.network.private_subnet_ids
  security_group_ids      = [module.network.lambda_security_group_id]
  environment             = local.app_env
  bucket_arns             = module.storage.bucket_arns
  kms_key_arn             = module.storage.kms_key_arn
  secret_arns             = [module.database.app_secret_arn, module.database.master_secret_arn, aws_secretsmanager_secret.stripe.arn]
  user_pool_arn           = module.identity.user_pool_arn
  email_from              = local.email_from
  jwt_issuer              = module.identity.issuer
  jwt_audiences           = [module.identity.web_client_id, module.identity.admin_client_id]
  cors_origins            = distinct(concat([local.web_url, local.admin_url], var.extra_web_urls))
  provisioned_concurrency = var.api_provisioned_concurrency
}

module "websocket" {
  source             = "../websocket"
  name               = local.name
  image_uri          = var.image_uri
  role_arn           = module.api.role_arn
  subnet_ids         = module.network.private_subnet_ids
  security_group_ids = [module.network.lambda_security_group_id]
  environment        = local.app_env
}

module "workers" {
  source             = "../workers"
  name               = local.name
  image_uri          = var.image_uri
  role_arn           = module.api.role_arn
  subnet_ids         = module.network.private_subnet_ids
  security_group_ids = [module.network.lambda_security_group_id]
  environment        = local.app_env
  kms_key_arn        = module.storage.kms_key_arn
}

module "workflows" {
  source              = "../workflows"
  name                = local.name
  worker_function_arn = module.workers.function_arn
}

module "scheduler" {
  source      = "../scheduler"
  name        = local.name
  queue_arns  = module.workers.queue_arns
  kms_key_arn = module.storage.kms_key_arn
}

module "waf" {
  source          = "../waf"
  providers       = { aws = aws, aws.us_east_1 = aws.us_east_1 }
  name            = local.name
  origin_domain   = module.api.http_api_domain
  api_domain      = local.api_domain
  certificate_arn = local.has_domain ? module.dns[0].edge_certificate_arn : null
}

module "observability" {
  source               = "../observability"
  name                 = local.name
  region               = local.region
  alert_emails         = var.alert_emails
  app_log_groups       = ["/aws/lambda/${local.name}-api", "/aws/lambda/${local.name}-worker", "/aws/lambda/${local.name}-ws"]
  api_function_name    = module.api.function_name
  worker_function_name = module.workers.function_name
  http_api_id          = module.api.http_api_id
  dlq_names            = module.workers.dlq_names
  queue_names          = module.workers.queue_names
  llm_daily_budget_usd = var.llm_monthly_budget_usd / 30
  depends_on           = [module.api, module.workers, module.websocket]
}

module "budgets" {
  source            = "../budgets"
  name              = local.name
  emails            = var.alert_emails
  monthly_limit_usd = var.monthly_budget_usd
  bedrock_limit_usd = var.llm_monthly_budget_usd
}

module "frontend" {
  count               = var.github_access_token == null ? 0 : 1
  source              = "../frontend"
  name                = local.name
  repository_url      = var.repository_url
  github_access_token = var.github_access_token
  branch              = var.frontend_branch
  stage               = var.environment == "prod" ? "PRODUCTION" : "DEVELOPMENT"
  zone_name           = var.zone_name
  web_domain          = local.has_domain ? "app.${var.zone_name}" : null
  admin_domain        = local.has_domain ? "admin.${var.zone_name}" : null
  web_client_id       = module.identity.web_client_id
  admin_client_id     = module.identity.admin_client_id
  common_env = {
    NEXT_PUBLIC_API_URL     = local.api_url
    NEXT_PUBLIC_WS_URL      = module.websocket.ws_url
    NEXT_PUBLIC_WS_MODE     = "apigw"
    NEXT_PUBLIC_AUTH_MODE   = "oidc"
    NEXT_PUBLIC_OIDC_ISSUER = module.identity.issuer
    NEXT_PUBLIC_OIDC_DOMAIN = "https://${module.identity.hosted_ui_domain}"
    NEXT_PUBLIC_WEB_URL     = local.web_url
    NEXT_PUBLIC_ADMIN_URL   = local.admin_url
    NEXT_PUBLIC_ENVIRONMENT = var.environment
  }
}
