# Composition root for one Azure environment (Australia East; NZ North for NZ-resident tenants if required).
terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

locals {
  name = "complymate-${var.environment}"
  tags = { Project = "complymate", Environment = var.environment, ManagedBy = "terraform", DataResidency = "AU" }
}

resource "azurerm_resource_group" "this" {
  name     = "rg-${local.name}"
  location = var.location
  tags     = local.tags
}

resource "azurerm_container_registry" "this" {
  name                = replace("${local.name}acr", "-", "")
  resource_group_name = azurerm_resource_group.this.name
  location            = var.location
  sku                 = "Premium"
  admin_enabled       = false
}

module "network" {
  source              = "../network"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  cidr                = var.vnet_cidr
}

module "observability" {
  source              = "../observability"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  alert_emails        = var.alert_emails
}

module "storage" {
  source              = "../storage"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  lock_audit_policy   = var.environment == "prod"
}

module "database" {
  source               = "../database"
  name                 = local.name
  location             = var.location
  resource_group_name  = azurerm_resource_group.this.name
  subnet_id            = module.network.postgres_subnet_id
  private_dns_zone_id  = module.network.postgres_dns_zone_id
  key_vault_id         = module.storage.key_vault_id
  sku_name             = var.db_sku
  high_availability    = var.environment == "prod"
  geo_redundant_backup = true
}

module "ai" {
  source              = "../ai"
  name                = local.name
  location            = var.location
  resource_group_name = azurerm_resource_group.this.name
  deploy_openai_chat  = var.foundry_endpoint == null
}

module "identity" {
  source              = "../identity"
  name                = local.name
  web_redirect_uris   = ["${var.web_url}/callback"]
  admin_redirect_uris = ["${var.admin_url}/callback"]
}

locals {
  app_env = {
    ENVIRONMENT                           = var.environment
    CLOUD_PROVIDER                        = "azure"
    DEFAULT_JURISDICTION                  = var.default_jurisdiction
    DB_SECRET_ARN                         = module.database.app_secret_name
    DB_ADMIN_SECRET_ARN                   = module.database.admin_secret_name
    AZURE_KEY_VAULT_URL                   = module.storage.key_vault_uri
    AZURE_STORAGE_ACCOUNT_URL             = trimsuffix(module.storage.storage_account_url, "/")
    DOCUMENTS_BUCKET                      = "documents"
    EXPORTS_BUCKET                        = "exports"
    AZURE_AUDIT_CONTAINER                 = "audit"
    AZURE_SERVICEBUS_NAMESPACE            = module.jobs.servicebus_namespace
    AZURE_OPENAI_ENDPOINT                 = module.ai.openai_endpoint
    AZURE_FOUNDRY_ENDPOINT                = coalesce(var.foundry_endpoint, module.ai.openai_endpoint)
    AZURE_DOCINTEL_ENDPOINT               = module.ai.docintel_endpoint
    AZURE_ACS_ENDPOINT                    = module.jobs.acs_endpoint
    AZURE_SUBSCRIPTION_ID                 = var.subscription_id
    AZURE_RESOURCE_GROUP                  = azurerm_resource_group.this.name
    AZURE_LOCATION                        = var.location
    LLM_MODEL_ID                          = var.llm_model_id
    LLM_FAST_MODEL_ID                     = var.llm_fast_model_id
    EMBEDDING_MODEL_ID                    = module.ai.embedding_deployment
    OIDC_ISSUER                           = var.oidc_issuer
    OIDC_AUDIENCE                         = module.identity.web_client_id
    WEB_BASE_URL                          = var.web_url
    ADMIN_BASE_URL                        = var.admin_url
    CORS_ORIGINS                          = jsonencode([var.web_url, var.admin_url])
    EMAIL_FROM                            = var.email_from
    WORKER_IMAGE                          = var.api_image
    APPLICATIONINSIGHTS_CONNECTION_STRING = module.observability.app_insights_connection_string
  }
}

module "container_apps" {
  source                     = "../container_apps"
  name                       = local.name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.this.name
  subnet_id                  = module.network.apps_subnet_id
  log_analytics_workspace_id = module.observability.workspace_id
  registry_server            = azurerm_container_registry.this.login_server
  registry_id                = azurerm_container_registry.this.id
  api_image                  = var.api_image
  web_image                  = var.web_image
  admin_image                = var.admin_image
  environment                = local.app_env
  storage_account_id         = module.storage.storage_account_id
  key_vault_id               = module.storage.key_vault_id
  servicebus_id              = module.jobs.servicebus_id
  openai_id                  = module.ai.openai_id
  docintel_id                = module.ai.docintel_id
  acs_id                     = module.jobs.acs_id
  zone_redundant             = var.environment == "prod"
  api_min_replicas           = var.environment == "prod" ? 2 : 1
}

module "jobs" {
  source                       = "../jobs"
  name                         = local.name
  location                     = var.location
  resource_group_name          = azurerm_resource_group.this.name
  container_app_environment_id = module.container_apps.environment_id
  identity_id                  = module.container_apps.identity_id
  registry_server              = azurerm_container_registry.this.login_server
  image                        = var.api_image
  environment                  = local.app_env_jobs
}

locals {
  # Jobs need the same settings as the API minus the Service Bus namespace (they don't consume queues).
  app_env_jobs = { for k, v in local.app_env : k => v if k != "AZURE_SERVICEBUS_NAMESPACE" }
}

module "front_door" {
  source              = "../front_door"
  name                = local.name
  resource_group_name = azurerm_resource_group.this.name
  origins = {
    api   = module.container_apps.fqdns["api"]
    web   = module.container_apps.fqdns["web"]
    admin = module.container_apps.fqdns["admin"]
  }
}

module "dns" {
  count               = var.zone_name == null ? 0 : 1
  source              = "../dns"
  resource_group_name = azurerm_resource_group.this.name
  zone_name           = var.zone_name
  cnames = {
    api   = trimprefix(module.front_door.endpoints["api"], "https://")
    app   = trimprefix(module.front_door.endpoints["web"], "https://")
    admin = trimprefix(module.front_door.endpoints["admin"], "https://")
  }
}

module "budgets" {
  source            = "../budgets"
  name              = local.name
  resource_group_id = azurerm_resource_group.this.id
  monthly_limit     = var.monthly_budget
  emails            = var.alert_emails
  start_date        = var.budget_start_date
}
