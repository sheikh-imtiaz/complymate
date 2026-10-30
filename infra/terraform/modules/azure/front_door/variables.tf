variable "name" { type = string }
variable "resource_group_name" { type = string }
variable "origins" {
  description = "map of app name → Container App FQDN (api, web, admin)"
  type        = map(string)
}
