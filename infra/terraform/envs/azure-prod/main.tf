# ComplyMate Azure prod (Australia East). Same container image and code as AWS; CLOUD_PROVIDER=azure.
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
    azuread = { source = "hashicorp/azuread", version = "~> 3.0" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "azurerm" {
    key = "azure-prod.tfstate"
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
}

# Points at the Entra External ID (customer) tenant that holds app registrations for sign-in.
provider "azuread" {
  tenant_id = var.external_id_tenant_id
}

module "stack" {
  source            = "../../modules/azure/stack"
  environment       = "prod"
  location          = var.location
  subscription_id   = var.subscription_id
  vnet_cidr         = var.vnet_cidr
  api_image         = var.api_image
  web_image         = var.web_image
  admin_image       = var.admin_image
  db_sku            = var.db_sku
  oidc_issuer       = var.oidc_issuer
  foundry_endpoint  = var.foundry_endpoint
  web_url           = var.web_url
  admin_url         = var.admin_url
  email_from        = var.email_from
  zone_name         = var.zone_name
  alert_emails      = var.alert_emails
  monthly_budget    = var.monthly_budget
  budget_start_date = var.budget_start_date
}

output "endpoints" { value = module.stack.endpoints }
output "registry" { value = module.stack.registry }
output "web_client_id" { value = module.stack.web_client_id }
output "admin_client_id" { value = module.stack.admin_client_id }
