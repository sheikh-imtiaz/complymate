terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
    random  = { source = "hashicorp/random", version = "~> 3.6" }
  }
}

resource "random_password" "admin" {
  length  = 40
  special = false
}

resource "random_password" "app" {
  length  = 40
  special = false
}

# Azure Database for PostgreSQL Flexible Server 16 + pgvector. Same schema, migrations and RLS as AWS.
resource "azurerm_postgresql_flexible_server" "this" {
  name                          = "${var.name}-pg"
  resource_group_name           = var.resource_group_name
  location                      = var.location
  version                       = "16"
  delegated_subnet_id           = var.subnet_id
  private_dns_zone_id           = var.private_dns_zone_id
  public_network_access_enabled = false
  administrator_login           = "complymate_owner"
  administrator_password        = random_password.admin.result
  sku_name                      = var.sku_name
  storage_mb                    = var.storage_mb
  storage_tier                  = "P10"
  backup_retention_days         = 35
  geo_redundant_backup_enabled  = var.geo_redundant_backup
  zone                          = "1"
  dynamic "high_availability" {
    for_each = var.high_availability ? [1] : []
    content {
      mode                      = "ZoneRedundant"
      standby_availability_zone = "2"
    }
  }
  lifecycle {
    ignore_changes = [zone, high_availability[0].standby_availability_zone]
  }
}

resource "azurerm_postgresql_flexible_server_configuration" "extensions" {
  name      = "azure.extensions"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "VECTOR,PGCRYPTO,PG_TRGM,PG_STAT_STATEMENTS"
}

resource "azurerm_postgresql_flexible_server_configuration" "ssl" {
  name      = "require_secure_transport"
  server_id = azurerm_postgresql_flexible_server.this.id
  value     = "on"
}

resource "azurerm_postgresql_flexible_server_database" "app" {
  name      = "complymate"
  server_id = azurerm_postgresql_flexible_server.this.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_key_vault_secret" "admin" {
  name         = "db-admin"
  key_vault_id = var.key_vault_id
  value = jsonencode({
    username = "complymate_owner", password = random_password.admin.result,
    host     = azurerm_postgresql_flexible_server.this.fqdn, port = 5432, dbname = "complymate"
  })
}

resource "azurerm_key_vault_secret" "app" {
  name         = "db-app"
  key_vault_id = var.key_vault_id
  value = jsonencode({
    username = "complymate_app", password = random_password.app.result,
    host     = azurerm_postgresql_flexible_server.this.fqdn, port = 5432, dbname = "complymate"
  })
}
