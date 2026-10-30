variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "cidr" {
  type    = string
  default = "10.50.0.0/16"
}
