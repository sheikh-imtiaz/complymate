terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name}-logs"
  location            = var.location
  resource_group_name = var.resource_group_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "this" {
  name                = "${var.name}-appi"
  location            = var.location
  resource_group_name = var.resource_group_name
  workspace_id        = azurerm_log_analytics_workspace.this.id
  application_type    = "web"
}

resource "azurerm_monitor_action_group" "alerts" {
  name                = "${var.name}-alerts"
  resource_group_name = var.resource_group_name
  short_name          = "complymate"
  dynamic "email_receiver" {
    for_each = var.alert_emails
    content {
      name          = "email-${email_receiver.key}"
      email_address = email_receiver.value
    }
  }
}

locals {
  # Same signals as the AWS alarms, from the same structured JSON logs.
  queries = {
    security-events   = { q = "ContainerAppConsoleLogs_CL | where Log_s has '\"security_event\"' | summarize c = count()", threshold = 20, severity = 2 }
    audit-chain-break = { q = "ContainerAppConsoleLogs_CL | where Log_s has 'audit_chain_break' or Log_s has 'AuditChainBreak' | summarize c = count()", threshold = 0, severity = 0 }
    screening-failed  = { q = "ContainerAppConsoleLogs_CL | where Log_s has 'ScreeningJobFailed' | summarize c = count()", threshold = 0, severity = 1 }
    api-errors        = { q = "ContainerAppConsoleLogs_CL | where Log_s has 'unhandled_error' | summarize c = count()", threshold = 5, severity = 2 }
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert_v2" "this" {
  for_each             = local.queries
  name                 = "${var.name}-${each.key}"
  resource_group_name  = var.resource_group_name
  location             = var.location
  scopes               = [azurerm_log_analytics_workspace.this.id]
  severity             = each.value.severity
  evaluation_frequency = "PT5M"
  window_duration      = "PT15M"
  criteria {
    query                   = each.value.q
    time_aggregation_method = "Total"
    metric_measure_column   = "c"
    operator                = "GreaterThan"
    threshold               = each.value.threshold
  }
  action {
    action_groups = [azurerm_monitor_action_group.alerts.id]
  }
}
