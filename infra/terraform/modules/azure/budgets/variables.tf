variable "name" { type = string }
variable "resource_group_id" { type = string }
variable "monthly_limit" {
  type    = number
  default = 800
}
variable "emails" { type = list(string) }
variable "start_date" {
  description = "First day of a month, RFC3339 (e.g. 2026-11-01T00:00:00Z)"
  type        = string
}
