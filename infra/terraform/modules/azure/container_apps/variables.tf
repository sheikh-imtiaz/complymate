variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "subnet_id" { type = string }
variable "log_analytics_workspace_id" { type = string }
variable "registry_server" { type = string }
variable "registry_id" { type = string }
variable "api_image" { type = string }
variable "web_image" { type = string }
variable "admin_image" { type = string }
variable "environment" { type = map(string) }
variable "storage_account_id" { type = string }
variable "key_vault_id" { type = string }
variable "servicebus_id" { type = string }
variable "openai_id" { type = string }
variable "docintel_id" { type = string }
variable "acs_id" { type = string }
variable "api_min_replicas" {
  type    = number
  default = 1
}
variable "zone_redundant" {
  type    = bool
  default = false
}
