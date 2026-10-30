variable "name" { type = string }
variable "image_uri" { type = string }
variable "subnet_ids" { type = list(string) }
variable "security_group_ids" { type = list(string) }
variable "environment" { type = map(string) }
variable "bucket_arns" { type = map(string) }
variable "kms_key_arn" { type = string }
variable "logs_kms_key_arn" {
  type    = string
  default = null
}
variable "secret_arns" { type = list(string) }
variable "user_pool_arn" { type = string }
variable "email_from" { type = string }
variable "jwt_issuer" { type = string }
variable "jwt_audiences" { type = list(string) }
variable "cors_origins" { type = list(string) }
variable "memory_mb" {
  type    = number
  default = 1536
}
variable "provisioned_concurrency" {
  type    = number
  default = 0
}
variable "log_retention_days" {
  type    = number
  default = 30
}
variable "throttle_burst" {
  type    = number
  default = 200
}
variable "throttle_rate" {
  type    = number
  default = 100
}
