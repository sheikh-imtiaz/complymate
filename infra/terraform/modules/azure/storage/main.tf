terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "this" {
  name                          = substr(replace("${var.name}-kv", "-", ""), 0, 24)
  location                      = var.location
  resource_group_name           = var.resource_group_name
  tenant_id                     = data.azurerm_client_config.current.tenant_id
  sku_name                      = "premium" # HSM-backed keys
  purge_protection_enabled      = true
  soft_delete_retention_days    = 90
  enable_rbac_authorization     = true
  public_network_access_enabled = true
  network_acls {
    bypass         = "AzureServices"
    default_action = var.restrict_network ? "Deny" : "Allow"
  }
}

resource "azurerm_role_assignment" "deployer_kv_admin" {
  scope                = azurerm_key_vault.this.id
  role_definition_name = "Key Vault Administrator"
  principal_id         = data.azurerm_client_config.current.object_id
}

# Wraps per-tenant document data keys (envelope encryption; see adapters/azure/key_vault_kms.py).
resource "azurerm_key_vault_key" "documents" {
  name         = "documents"
  key_vault_id = azurerm_key_vault.this.id
  key_type     = "RSA-HSM"
  key_size     = 3072
  key_opts     = ["wrapKey", "unwrapKey"]
  rotation_policy {
    automatic {
      time_before_expiry = "P30D"
    }
    expire_after         = "P2Y"
    notify_before_expiry = "P29D"
  }
  depends_on = [azurerm_role_assignment.deployer_kv_admin]
}

resource "azurerm_storage_account" "this" {
  name                              = substr(replace("${var.name}st", "-", ""), 0, 24)
  resource_group_name               = var.resource_group_name
  location                          = var.location
  account_tier                      = "Standard"
  account_replication_type          = var.replication
  min_tls_version                   = "TLS1_2"
  https_traffic_only_enabled        = true
  allow_nested_items_to_be_public   = false
  shared_access_key_enabled         = false # Entra ID (managed identity) only
  infrastructure_encryption_enabled = true
  blob_properties {
    versioning_enabled = true
    delete_retention_policy {
      days = 30
    }
    container_delete_retention_policy {
      days = 30
    }
  }
}

resource "azurerm_storage_container" "this" {
  for_each              = toset(["documents", "exports", "audit"])
  name                  = each.value
  storage_account_id    = azurerm_storage_account.this.id
  container_access_type = "private"
}

# Audit archive: time-based immutability, locked, 7 years (write-once, read-many).
resource "azurerm_storage_container_immutability_policy" "audit" {
  storage_container_resource_manager_id = azurerm_storage_container.this["audit"].id
  immutability_period_in_days           = var.audit_retention_days
  protected_append_writes_all_enabled   = false
  locked                                = var.lock_audit_policy
}

resource "azurerm_storage_management_policy" "this" {
  storage_account_id = azurerm_storage_account.this.id
  rule {
    name    = "expire-exports"
    enabled = true
    filters {
      prefix_match = ["exports/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        delete_after_days_since_modification_greater_than = 30
      }
    }
  }
  rule {
    name    = "cool-documents"
    enabled = true
    filters {
      prefix_match = ["documents/"]
      blob_types   = ["blockBlob"]
    }
    actions {
      base_blob {
        tier_to_cool_after_days_since_modification_greater_than = 90
      }
    }
  }
}
