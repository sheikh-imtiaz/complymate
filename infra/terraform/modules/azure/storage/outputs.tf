output "key_vault_id" { value = azurerm_key_vault.this.id }
output "key_vault_uri" { value = azurerm_key_vault.this.vault_uri }
output "storage_account_id" { value = azurerm_storage_account.this.id }
output "storage_account_url" { value = azurerm_storage_account.this.primary_blob_endpoint }
