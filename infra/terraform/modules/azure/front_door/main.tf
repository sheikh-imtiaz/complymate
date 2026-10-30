terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.14" }
  }
}

resource "azurerm_cdn_frontdoor_profile" "this" {
  name                = "${var.name}-fd"
  resource_group_name = var.resource_group_name
  sku_name            = "Premium_AzureFrontDoor" # managed WAF rule sets
}

resource "azurerm_cdn_frontdoor_firewall_policy" "this" {
  name                = replace("${var.name}waf", "-", "")
  resource_group_name = var.resource_group_name
  sku_name            = azurerm_cdn_frontdoor_profile.this.sku_name
  mode                = "Prevention"
  managed_rule {
    type    = "Microsoft_DefaultRuleSet"
    version = "2.1"
    action  = "Block"
  }
  managed_rule {
    type    = "Microsoft_BotManagerRuleSet"
    version = "1.1"
    action  = "Block"
  }
  custom_rule {
    name                           = "ratelimit"
    enabled                        = true
    priority                       = 1
    type                           = "RateLimitRule"
    rate_limit_duration_in_minutes = 5
    rate_limit_threshold           = 2000
    action                         = "Block"
    match_condition {
      match_variable = "RemoteAddr"
      operator       = "IPMatch"
      match_values   = ["0.0.0.0/0", "::/0"]
    }
  }
}

resource "azurerm_cdn_frontdoor_endpoint" "this" {
  for_each                 = var.origins
  name                     = "${var.name}-${each.key}"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
}

resource "azurerm_cdn_frontdoor_origin_group" "this" {
  for_each                 = var.origins
  name                     = each.key
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
  load_balancing {}
  health_probe {
    path                = each.key == "api" ? "/health" : "/"
    protocol            = "Https"
    interval_in_seconds = 60
    request_type        = "GET"
  }
}

resource "azurerm_cdn_frontdoor_origin" "this" {
  for_each                       = var.origins
  name                           = each.key
  cdn_frontdoor_origin_group_id  = azurerm_cdn_frontdoor_origin_group.this[each.key].id
  enabled                        = true
  host_name                      = each.value
  origin_host_header             = each.value
  certificate_name_check_enabled = true
  https_port                     = 443
  http_port                      = 80
}

resource "azurerm_cdn_frontdoor_route" "this" {
  for_each                      = var.origins
  name                          = each.key
  cdn_frontdoor_endpoint_id     = azurerm_cdn_frontdoor_endpoint.this[each.key].id
  cdn_frontdoor_origin_group_id = azurerm_cdn_frontdoor_origin_group.this[each.key].id
  cdn_frontdoor_origin_ids      = [azurerm_cdn_frontdoor_origin.this[each.key].id]
  supported_protocols           = ["Https"]
  patterns_to_match             = ["/*"]
  forwarding_protocol           = "HttpsOnly"
  https_redirect_enabled        = false
  link_to_default_domain        = true
}

resource "azurerm_cdn_frontdoor_security_policy" "this" {
  name                     = "${var.name}-waf"
  cdn_frontdoor_profile_id = azurerm_cdn_frontdoor_profile.this.id
  security_policies {
    firewall {
      cdn_frontdoor_firewall_policy_id = azurerm_cdn_frontdoor_firewall_policy.this.id
      association {
        patterns_to_match = ["/*"]
        dynamic "domain" {
          for_each = azurerm_cdn_frontdoor_endpoint.this
          content {
            cdn_frontdoor_domain_id = domain.value.id
          }
        }
      }
    }
  }
}
