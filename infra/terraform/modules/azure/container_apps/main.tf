terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

# The same API/worker image as AWS Lambda; here it runs as long-lived containers (uvicorn / worker loop).
resource "azurerm_container_app_environment" "this" {
  name                           = "${var.name}-cae"
  location                       = var.location
  resource_group_name            = var.resource_group_name
  log_analytics_workspace_id     = var.log_analytics_workspace_id
  infrastructure_subnet_id       = var.subnet_id
  internal_load_balancer_enabled = false
  zone_redundancy_enabled        = var.zone_redundant
  workload_profile {
    name                  = "Consumption"
    workload_profile_type = "Consumption"
  }
}

resource "azurerm_user_assigned_identity" "app" {
  name                = "${var.name}-app"
  location            = var.location
  resource_group_name = var.resource_group_name
}

locals {
  apps = {
    api = {
      image = var.api_image, port = 8080, external = true, min = var.api_min_replicas, max = 10,
      cpu   = 1.0, memory = "2Gi", args = [], env = merge(var.environment, { RUN_MODE = "api" })
    }
    worker = {
      image = var.api_image, port = null, external = false, min = 1, max = 5,
      cpu   = 1.0, memory = "2Gi", args = ["worker"], env = merge(var.environment, { RUN_MODE = "worker", RUN_SCHEDULES = "false" })
    }
    web = {
      image = var.web_image, port = 3000, external = true, min = 1, max = 5, cpu = 0.5, memory = "1Gi", args = [], env = {}
    }
    admin = {
      image = var.admin_image, port = 3001, external = true, min = 1, max = 2, cpu = 0.5, memory = "1Gi", args = [], env = {}
    }
  }
}

resource "azurerm_container_app" "this" {
  for_each                     = local.apps
  name                         = "${var.name}-${each.key}"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = var.resource_group_name
  revision_mode                = "Single"
  workload_profile_name        = "Consumption"

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.app.id]
  }

  registry {
    server   = var.registry_server
    identity = azurerm_user_assigned_identity.app.id
  }

  dynamic "ingress" {
    for_each = each.value.port == null ? [] : [1]
    content {
      external_enabled = each.value.external
      target_port      = each.value.port
      transport        = "auto" # HTTP/1.1 + WebSockets for /ws/chat
      traffic_weight {
        latest_revision = true
        percentage      = 100
      }
    }
  }

  template {
    min_replicas = each.value.min
    max_replicas = each.value.max
    container {
      name   = each.key
      image  = each.value.image
      cpu    = each.value.cpu
      memory = each.value.memory
      args   = each.value.args
      env {
        name  = "AZURE_CLIENT_ID"
        value = azurerm_user_assigned_identity.app.client_id
      }
      dynamic "env" {
        for_each = each.value.env
        content {
          name  = env.key
          value = env.value
        }
      }
      dynamic "liveness_probe" {
        for_each = each.key == "api" ? [1] : []
        content {
          transport = "HTTP"
          port      = 8080
          path      = "/health"
        }
      }
    }
    dynamic "http_scale_rule" {
      for_each = each.value.port == null ? [] : [1]
      content {
        name                = "http"
        concurrent_requests = "50"
      }
    }
  }
}

# Least-privilege data-plane roles for the app identity (no keys or connection strings anywhere).
resource "azurerm_role_assignment" "app" {
  for_each = {
    blob    = { scope = var.storage_account_id, role = "Storage Blob Data Contributor" }
    secrets = { scope = var.key_vault_id, role = "Key Vault Secrets User" }
    crypto  = { scope = var.key_vault_id, role = "Key Vault Crypto User" }
    sbsend  = { scope = var.servicebus_id, role = "Azure Service Bus Data Sender" }
    sbrecv  = { scope = var.servicebus_id, role = "Azure Service Bus Data Receiver" }
    openai  = { scope = var.openai_id, role = "Cognitive Services OpenAI User" }
    docint  = { scope = var.docintel_id, role = "Cognitive Services User" }
    acs     = { scope = var.acs_id, role = "Contributor" }
    acr     = { scope = var.registry_id, role = "AcrPull" }
  }
  scope                = each.value.scope
  role_definition_name = each.value.role
  principal_id         = azurerm_user_assigned_identity.app.principal_id
}
