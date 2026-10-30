terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

locals {
  apps = {
    web = {
      root   = "apps/web"
      domain = var.web_domain
      env    = merge(var.common_env, { NEXT_PUBLIC_OIDC_CLIENT_ID = var.web_client_id, NEXT_PUBLIC_APP = "web" })
    }
    platform-admin = {
      root   = "apps/platform-admin"
      domain = var.admin_domain
      env    = merge(var.common_env, { NEXT_PUBLIC_OIDC_CLIENT_ID = var.admin_client_id, NEXT_PUBLIC_APP = "platform-admin" })
    }
  }
}

resource "aws_amplify_app" "this" {
  for_each     = local.apps
  name         = "${var.name}-${each.key}"
  repository   = var.repository_url
  access_token = var.github_access_token
  platform     = "WEB_COMPUTE"

  build_spec = <<-YAML
    version: 1
    applications:
      - appRoot: ${each.value.root}
        frontend:
          phases:
            preBuild:
              commands:
                - corepack enable
                - cd ../.. && pnpm install --frozen-lockfile && cd -
            build:
              commands:
                - pnpm run build
          artifacts:
            baseDirectory: .next
            files:
              - '**/*'
          cache:
            paths:
              - .next/cache/**/*
              - ../../node_modules/**/*
  YAML

  environment_variables = merge(each.value.env, {
    AMPLIFY_MONOREPO_APP_ROOT = each.value.root
    AMPLIFY_DIFF_DEPLOY       = "false"
    _CUSTOM_IMAGE             = "amplify:al2023"
  })
}

resource "aws_amplify_branch" "main" {
  for_each          = aws_amplify_app.this
  app_id            = each.value.id
  branch_name       = var.branch
  framework         = "Next.js - SSR"
  stage             = var.stage
  enable_auto_build = true
}

resource "aws_amplify_domain_association" "this" {
  for_each              = { for k, v in local.apps : k => v if v.domain != null }
  app_id                = aws_amplify_app.this[each.key].id
  domain_name           = var.zone_name
  wait_for_verification = false
  sub_domain {
    branch_name = aws_amplify_branch.main[each.key].branch_name
    prefix      = trimsuffix(replace(each.value.domain, var.zone_name, ""), ".")
  }
}
