variable "name" { type = string }
variable "region" { type = string }
variable "alert_emails" {
  type    = list(string)
  default = []
}
variable "app_log_groups" { type = list(string) }
variable "api_function_name" { type = string }
variable "worker_function_name" { type = string }
variable "http_api_id" { type = string }
variable "dlq_names" { type = map(string) }
variable "queue_names" { type = map(string) }
variable "llm_daily_budget_usd" {
  type    = number
  default = 25
}
