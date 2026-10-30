variable "subscription_id" { type = string }
variable "external_id_tenant_id" { type = string }
variable "location" {
  type    = string
  default = "australiaeast"
}
variable "vnet_cidr" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "admin_image" { type = string }
variable "db_sku" { type = string }
variable "oidc_issuer" { type = string }
variable "foundry_endpoint" {
  type    = string
  default = null
}
variable "web_url" { type = string }
variable "admin_url" { type = string }
variable "email_from" { type = string }
variable "zone_name" {
  type    = string
  default = null
}
variable "alert_emails" {
  type    = list(string)
  default = []
}
variable "monthly_budget" { type = number }
variable "budget_start_date" { type = string }
