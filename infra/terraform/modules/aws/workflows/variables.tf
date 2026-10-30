variable "name" { type = string }
variable "worker_function_arn" { type = string }
variable "log_retention_days" {
  type    = number
  default = 30
}
