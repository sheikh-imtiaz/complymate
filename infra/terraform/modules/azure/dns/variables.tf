variable "resource_group_name" { type = string }
variable "zone_name" { type = string }
variable "cnames" {
  description = "subdomain → Front Door endpoint host (custom domains are then validated in Front Door)"
  type        = map(string)
  default     = {}
}
