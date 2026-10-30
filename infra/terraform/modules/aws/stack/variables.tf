variable "environment" {
  type = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "environment must be dev, staging or prod"
  }
}
variable "image_uri" {
  description = "ECR image (API + workers), e.g. 123456789012.dkr.ecr.ap-southeast-2.amazonaws.com/complymate-api:<git-sha>"
  type        = string
}
variable "zone_name" {
  description = "Route 53 public zone (e.g. complymate.com.au). null = no custom domains (CloudFront/Amplify defaults)."
  type        = string
  default     = null
}
variable "web_url" {
  description = "Tenant app URL when no custom domain (set to the Amplify default domain after the first apply)"
  type        = string
  default     = "http://localhost:3000"
}
variable "admin_url" {
  type    = string
  default = "http://localhost:3001"
}
variable "extra_web_urls" {
  type    = list(string)
  default = []
}
variable "email_from" {
  type    = string
  default = null
}
variable "alert_emails" {
  type    = list(string)
  default = []
}
variable "vpc_cidr" {
  type    = string
  default = "10.40.0.0/16"
}
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
variable "db_min_acu" {
  type    = number
  default = 0.5
}
variable "db_max_acu" {
  type    = number
  default = 4
}
variable "db_instance_count" {
  type    = number
  default = 1
}
variable "api_provisioned_concurrency" {
  type    = number
  default = 0
}
variable "llm_model_id" {
  description = "Bedrock model or inference profile for Claude Sonnet (AU cross-region profile keeps data in Australia)"
  type        = string
  default     = "au.anthropic.claude-sonnet-4-5-20250929-v1:0"
}
variable "llm_fast_model_id" {
  type    = string
  default = "au.anthropic.claude-haiku-4-5-20251001-v1:0"
}
variable "llm_monthly_budget_usd" {
  type    = number
  default = 200
}
variable "monthly_budget_usd" {
  type    = number
  default = 500
}
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
variable "repository_url" {
  type    = string
  default = "https://github.com/sheikh-imtiaz/complymate"
}
variable "github_access_token" {
  description = "Token for Amplify Hosting. null skips the frontend module (deploy the apps another way)."
  type        = string
  default     = null
  sensitive   = true
}
variable "frontend_branch" {
  type    = string
  default = "main"
}
