# Bootstrap stack (run once per AWS account with local state, then migrate state into the bucket it creates):
#   terraform init && terraform apply -var account_name=dev -var github_repo=sheikh-imtiaz/complymate
terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = { Project = "complymate", ManagedBy = "terraform", Stack = "global", Account = var.account_name }
  }
}

variable "region" {
  type    = string
  default = "ap-southeast-2"
}

variable "account_name" {
  description = "dev | staging | prod (one AWS account per environment, via AWS Organizations)"
  type        = string
}

variable "github_repo" {
  description = "owner/repo allowed to assume the deploy role through GitHub OIDC"
  type        = string
}
