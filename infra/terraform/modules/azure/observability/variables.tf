variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "alert_emails" {
  type    = list(string)
  default = []
}
