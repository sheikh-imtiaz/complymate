output "endpoints" { value = { for k, e in azurerm_cdn_frontdoor_endpoint.this : k => "https://${e.host_name}" } }
output "profile_id" { value = azurerm_cdn_frontdoor_profile.this.id }
