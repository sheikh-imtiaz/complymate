terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

resource "azurerm_consumption_budget_resource_group" "this" {
  name              = "${var.name}-monthly"
  resource_group_id = var.resource_group_id
  amount            = var.monthly_limit
  time_grain        = "Monthly"
  time_period {
    start_date = var.start_date
  }
  dynamic "notification" {
    for_each = [50, 80, 100]
    content {
      enabled        = true
      threshold      = notification.value
      operator       = "GreaterThan"
      threshold_type = notification.value == 100 ? "Forecasted" : "Actual"
      contact_emails = var.emails
    }
  }
}
