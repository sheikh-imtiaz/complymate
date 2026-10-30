# ComplyMate AWS dev (ap-southeast-2, Sydney). All tenant data stays in Australia; DR backups go to Melbourne.
#   terraform init -backend-config="bucket=complymate-tfstate-dev-<account-id>" -backend-config="dynamodb_table=complymate-tflock-dev"
#   terraform apply -var image_uri=<ecr-uri>:<sha>
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws    = { source = "hashicorp/aws", version = "~> 5.80" }
    random = { source = "hashicorp/random", version = "~> 3.6" }
  }
  backend "s3" {
    key     = "aws-dev/terraform.tfstate"
    region  = "ap-southeast-2"
    encrypt = true
  }
}

locals {
  tags = { Project = "complymate", Environment = "dev", ManagedBy = "terraform", DataResidency = "AU" }
}

provider "aws" {
  region = "ap-southeast-2"
  default_tags {
    tags = local.tags
  }
}

provider "aws" {
  alias  = "us_east_1" # CloudFront WAF + certificates
  region = "us-east-1"
  default_tags {
    tags = local.tags
  }
}

provider "aws" {
  alias  = "dr" # Melbourne: cross-region backup copies stay in Australia
  region = "ap-southeast-4"
  default_tags {
    tags = local.tags
  }
}

module "stack" {
  source    = "../../modules/aws/stack"
  providers = { aws = aws, aws.us_east_1 = aws.us_east_1, aws.dr = aws.dr }

  environment                 = "dev"
  image_uri                   = var.image_uri
  zone_name                   = var.zone_name
  web_url                     = var.web_url
  admin_url                   = var.admin_url
  extra_web_urls              = var.extra_web_urls
  alert_emails                = var.alert_emails
  vpc_cidr                    = var.vpc_cidr
  az_count                    = var.az_count
  enable_nat_gateway          = var.enable_nat_gateway
  endpoint_services           = var.endpoint_services
  db_min_acu                  = var.db_min_acu
  db_max_acu                  = var.db_max_acu
  db_instance_count           = var.db_instance_count
  api_provisioned_concurrency = var.api_provisioned_concurrency
  llm_monthly_budget_usd      = var.llm_monthly_budget_usd
  monthly_budget_usd          = var.monthly_budget_usd
  stripe_price_solo           = var.stripe_price_solo
  stripe_price_practice       = var.stripe_price_practice
  stripe_price_onboarding     = var.stripe_price_onboarding
  github_access_token         = var.github_access_token
}

output "api_url" { value = module.stack.api_url }
output "ws_url" { value = module.stack.ws_url }
output "worker_function" { value = module.stack.worker_function }
output "cognito_user_pool_id" { value = module.stack.cognito_user_pool_id }
output "cognito_web_client_id" { value = module.stack.cognito_web_client_id }
output "cognito_admin_client_id" { value = module.stack.cognito_admin_client_id }
output "cognito_hosted_ui" { value = module.stack.cognito_hosted_ui }
output "oidc_issuer" { value = module.stack.oidc_issuer }
output "frontend_domains" { value = module.stack.frontend_domains }
output "stripe_secret_arn" { value = module.stack.stripe_secret_arn }
