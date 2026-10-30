variable "environment" { type = string }
variable "location" {
  type    = string
  default = "australiaeast"
}
variable "subscription_id" { type = string }
variable "default_jurisdiction" {
  type    = string
  default = "AU"
}
variable "vnet_cidr" {
  type    = string
  default = "10.50.0.0/16"
}
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "admin_image" { type = string }
variable "db_sku" {
  type    = string
  default = "GP_Standard_D2ds_v5"
}
variable "oidc_issuer" {
  description = "Entra External ID issuer, e.g. https://<tenant>.ciamlogin.com/<tenant-id>/v2.0"
  type        = string
}
variable "foundry_endpoint" {
  description = "Azure AI Foundry endpoint serving Claude (OpenAI-compatible). null = use the Azure OpenAI chat deployment."
  type        = string
  default     = null
}
variable "llm_model_id" {
  type    = string
  default = "claude-sonnet-4-5"
}
variable "llm_fast_model_id" {
  type    = string
  default = "claude-haiku-4-5"
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
variable "monthly_budget" {
  type    = number
  default = 800
}
variable "budget_start_date" { type = string }
