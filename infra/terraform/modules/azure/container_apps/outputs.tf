output "environment_id" { value = azurerm_container_app_environment.this.id }
output "identity_id" { value = azurerm_user_assigned_identity.app.id }
output "identity_principal_id" { value = azurerm_user_assigned_identity.app.principal_id }
output "fqdns" { value = { for k, a in azurerm_container_app.this : k => try(a.ingress[0].fqdn, null) } }
