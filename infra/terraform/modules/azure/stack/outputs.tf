output "resource_group" { value = azurerm_resource_group.this.name }
output "registry" { value = azurerm_container_registry.this.login_server }
output "endpoints" { value = module.front_door.endpoints }
output "container_app_fqdns" { value = module.container_apps.fqdns }
output "web_client_id" { value = module.identity.web_client_id }
output "admin_client_id" { value = module.identity.admin_client_id }
