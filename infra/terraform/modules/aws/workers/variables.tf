variable "name" { type = string }
variable "image_uri" { type = string }
variable "role_arn" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
variable "environment" { type = map(string) }
variable "kms_key_arn" { type = string }
variable "memory_mb" {
  type    = number
  default = 2048
}
variable "timeout_seconds" {
  type    = number
  default = 900
}
variable "log_retention_days" {
  type    = number
  default = 30
}
