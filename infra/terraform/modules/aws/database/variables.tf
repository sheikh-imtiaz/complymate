variable "name" { type = string }
variable "vpc_id" { type = string }
variable "vpc_cidr" { type = string }
variable "subnet_ids" { type = list(string) }
variable "client_security_group_ids" { type = list(string) }
variable "kms_key_arn" { type = string }
variable "engine_version" {
  type    = string
  default = "16.4"
}
variable "min_acu" {
  description = "0 lets dev auto-pause; use >= 0.5 for staging/prod"
  type        = number
  default     = 0.5
}
variable "max_acu" {
  type    = number
  default = 8
}
variable "instance_count" {
  description = "1 writer for dev; 2 (writer + reader in another AZ) for prod"
  type        = number
  default     = 1
}
variable "deletion_protection" {
  type    = bool
  default = true
}
variable "backup_retention_days" {
  type    = number
  default = 35
}
