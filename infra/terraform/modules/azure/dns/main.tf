terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

resource "azurerm_dns_zone" "this" {
  name                = var.zone_name
  resource_group_name = var.resource_group_name
}

resource "azurerm_dns_cname_record" "apps" {
  for_each            = var.cnames
  name                = each.key
  zone_name           = azurerm_dns_zone.this.name
  resource_group_name = var.resource_group_name
  ttl                 = 300
  record              = each.value
}
