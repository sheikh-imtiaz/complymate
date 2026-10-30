terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

resource "azurerm_servicebus_namespace" "this" {
  name                = "${var.name}-sb"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "Standard"
  local_auth_enabled  = false
  minimum_tls_version = "1.2"
}

resource "azurerm_servicebus_queue" "this" {
  for_each                             = toset(["ocr", "screening", "exports", "notifications", "audit"])
  name                                 = each.value
  namespace_id                         = azurerm_servicebus_namespace.this.id
  max_delivery_count                   = 5
  dead_lettering_on_message_expiration = true
  lock_duration                        = "PT5M"
}

resource "azurerm_communication_service" "this" {
  name                = "${var.name}-acs"
  resource_group_name = var.resource_group_name
  data_location       = "Australia"
}

resource "azurerm_email_communication_service" "this" {
  name                = "${var.name}-email"
  resource_group_name = var.resource_group_name
  data_location       = "Australia"
}

locals {
  # Mirrors complymate.workers.entry.DEFAULT_SCHEDULES (UTC cron; Sydney 01:00 ≈ 14:00/15:00 UTC).
  schedules = {
    refresh-watchlists   = { cron = "0 15 * * *", task = "refresh_watchlists" }
    nightly-rescreen     = { cron = "0 16 * * *", task = "nightly_rescreen" }
    verify-audit-chain   = { cron = "30 16 * * *", task = "verify_audit_chain" }
    archive-audit-events = { cron = "*/15 * * * *", task = "archive_audit_events" }
    send-reminders       = { cron = "0 21 * * *", task = "send_reminders" }
  }
}

resource "azurerm_container_app_job" "scheduled" {
  for_each                     = local.schedules
  name                         = substr("${var.name}-${each.key}", 0, 32)
  location                     = var.location
  resource_group_name          = var.resource_group_name
  container_app_environment_id = var.container_app_environment_id
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 1
  identity {
    type         = "UserAssigned"
    identity_ids = [var.identity_id]
  }
  schedule_trigger_config {
    cron_expression          = each.value.cron
    parallelism              = 1
    replica_completion_count = 1
  }
  registry {
    server   = var.registry_server
    identity = var.identity_id
  }
  template {
    container {
      name   = "job"
      image  = var.image
      cpu    = 0.5
      memory = "1Gi"
      args   = ["job", each.value.task, "{}"]
      dynamic "env" {
        for_each = var.environment
        content {
          name  = env.key
          value = env.value
        }
      }
    }
  }
}
