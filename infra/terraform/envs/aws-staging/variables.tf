variable "image_uri" { type = string }
variable "zone_name" {
  type    = string
  default = null
}
variable "web_url" {
  type    = string
  default = "http://localhost:3000"
}
variable "admin_url" {
  type    = string
  default = "http://localhost:3001"
}
variable "extra_web_urls" {
  type    = list(string)
  default = []
}
variable "alert_emails" {
  type    = list(string)
  default = []
}
variable "vpc_cidr" { type = string }
variable "az_count" {
  type    = number
  default = 2
}
variable "enable_nat_gateway" {
  type    = bool
  default = true
}
variable "endpoint_services" {
  type    = list(string)
  default = ["secretsmanager", "sqs", "kms", "bedrock-runtime"]
}
variable "db_min_acu" { type = number }
variable "db_max_acu" { type = number }
variable "db_instance_count" { type = number }
variable "api_provisioned_concurrency" {
  type    = number
  default = 0
}
variable "llm_monthly_budget_usd" { type = number }
variable "monthly_budget_usd" { type = number }
variable "stripe_price_solo" {
  type    = string
  default = ""
}
variable "stripe_price_practice" {
  type    = string
  default = ""
}
variable "stripe_price_onboarding" {
  type    = string
  default = ""
}
variable "github_access_token" {
  type      = string
  default   = null
  sensitive = true
}
