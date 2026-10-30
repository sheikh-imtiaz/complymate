variable "name" { type = string }
variable "image_uri" { type = string }
variable "role_arn" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
variable "environment" { type = map(string) }
variable "stage_name" {
  type    = string
  default = "live"
}
variable "log_retention_days" {
  type    = number
  default = 30
}
