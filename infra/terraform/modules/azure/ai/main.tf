terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

# Azure OpenAI (embeddings + optional chat model), Document Intelligence (ID OCR), Content Safety.
# Claude on Azure AI Foundry is deployed from the Foundry portal/model catalog; set foundry_endpoint in the stack.
# Check which models are offered in the region before promising data residency.
resource "azurerm_cognitive_account" "openai" {
  name                  = "${var.name}-aoai"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "OpenAI"
  sku_name              = "S0"
  custom_subdomain_name = "${var.name}-aoai"
  local_auth_enabled    = false
}

resource "azurerm_cognitive_deployment" "embeddings" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }
  sku {
    name     = "Standard"
    capacity = 50
  }
}

resource "azurerm_cognitive_deployment" "chat" {
  count                = var.deploy_openai_chat ? 1 : 0
  name                 = var.chat_model
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = var.chat_model
    version = var.chat_model_version
  }
  sku {
    name     = "Standard"
    capacity = 30
  }
}

resource "azurerm_cognitive_account" "docintel" {
  name                  = "${var.name}-docintel"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "FormRecognizer"
  sku_name              = "S0"
  custom_subdomain_name = "${var.name}-docintel"
  local_auth_enabled    = false
}

resource "azurerm_cognitive_account" "content_safety" {
  name                  = "${var.name}-safety"
  location              = var.location
  resource_group_name   = var.resource_group_name
  kind                  = "ContentSafety"
  sku_name              = "S0"
  custom_subdomain_name = "${var.name}-safety"
  local_auth_enabled    = false
}
