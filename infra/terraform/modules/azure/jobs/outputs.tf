output "servicebus_namespace" { value = azurerm_servicebus_namespace.this.name }
output "servicebus_id" { value = azurerm_servicebus_namespace.this.id }
# ACS endpoint host is <name>.<data-location>.communication.azure.com
output "acs_endpoint" { value = "https://${azurerm_communication_service.this.name}.australia.communication.azure.com" }
output "acs_id" { value = azurerm_communication_service.this.id }
