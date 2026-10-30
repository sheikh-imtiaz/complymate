output "fqdn" { value = azurerm_postgresql_flexible_server.this.fqdn }
output "app_password" {
  value     = random_password.app.result
  sensitive = true
}
output "app_secret_name" { value = azurerm_key_vault_secret.app.name }
output "admin_secret_name" { value = azurerm_key_vault_secret.admin.name }
