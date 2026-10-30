variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "container_app_environment_id" { type = string }
variable "identity_id" { type = string }
variable "registry_server" { type = string }
variable "image" { type = string }
variable "environment" { type = map(string) }
