terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  account = data.aws_caller_identity.current.account_id
  region  = data.aws_region.current.name
}

# ---------------- shared Lambda execution role (API, workers, websocket) ----------------
data "aws_iam_policy_document" "lambda_trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "app" {
  name               = "${var.name}-app"
  assume_role_policy = data.aws_iam_policy_document.lambda_trust.json
}

resource "aws_iam_role_policy_attachment" "vpc" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

resource "aws_iam_role_policy_attachment" "xray" {
  role       = aws_iam_role.app.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

data "aws_iam_policy_document" "app" {
  statement {
    sid       = "Buckets"
    actions   = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:PutObjectRetention"]
    resources = flatten([for arn in values(var.bucket_arns) : [arn, "${arn}/*"]])
  }
  statement {
    sid       = "Kms"
    actions   = ["kms:Encrypt", "kms:Decrypt", "kms:GenerateDataKey", "kms:DescribeKey"]
    resources = [var.kms_key_arn]
  }
  statement {
    sid       = "Secrets"
    actions   = ["secretsmanager:GetSecretValue"]
    resources = var.secret_arns
  }
  statement {
    sid       = "Queues"
    actions   = ["sqs:SendMessage", "sqs:ReceiveMessage", "sqs:DeleteMessage", "sqs:GetQueueAttributes", "sqs:ChangeMessageVisibility"]
    resources = ["arn:aws:sqs:${local.region}:${local.account}:${var.name}-*"]
  }
  statement {
    sid       = "Bedrock"
    actions   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream", "bedrock:ApplyGuardrail", "bedrock:Converse", "bedrock:ConverseStream"]
    resources = ["*"]
  }
  statement {
    sid       = "Textract"
    actions   = ["textract:AnalyzeID", "textract:AnalyzeDocument", "textract:DetectDocumentText"]
    resources = ["*"]
  }
  statement {
    sid       = "Ses"
    actions   = ["ses:SendEmail", "ses:SendRawEmail"]
    resources = ["*"]
    condition {
      test     = "StringLike"
      variable = "ses:FromAddress"
      values   = [var.email_from]
    }
  }
  statement {
    sid = "Cognito"
    actions = ["cognito-idp:AdminCreateUser", "cognito-idp:AdminGetUser", "cognito-idp:AdminDisableUser",
      "cognito-idp:AdminEnableUser", "cognito-idp:AdminUserGlobalSignOut", "cognito-idp:AdminSetUserMFAPreference",
    "cognito-idp:ListUsers"]
    resources = [var.user_pool_arn]
  }
  statement {
    sid       = "Workflows"
    actions   = ["states:StartExecution"]
    resources = ["arn:aws:states:${local.region}:${local.account}:stateMachine:${var.name}-*"]
  }
  statement {
    sid       = "Schedules"
    actions   = ["scheduler:CreateSchedule", "scheduler:UpdateSchedule", "scheduler:DeleteSchedule", "scheduler:GetSchedule"]
    resources = ["arn:aws:scheduler:${local.region}:${local.account}:schedule/${var.name}/*"]
  }
  statement {
    sid       = "PassSchedulerRole"
    actions   = ["iam:PassRole"]
    resources = ["arn:aws:iam::${local.account}:role/${var.name}-scheduler"]
  }
  statement {
    sid       = "WebSocketPush"
    actions   = ["execute-api:ManageConnections"]
    resources = ["arn:aws:execute-api:${local.region}:${local.account}:*/*/POST/@connections/*"]
  }
}

resource "aws_iam_role_policy" "app" {
  name   = "${var.name}-app"
  role   = aws_iam_role.app.id
  policy = data.aws_iam_policy_document.app.json
}

# ---------------- API Lambda (FastAPI via Mangum) ----------------
resource "aws_cloudwatch_log_group" "api" {
  name              = "/aws/lambda/${var.name}-api"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_lambda_function" "api" {
  function_name = "${var.name}-api"
  role          = aws_iam_role.app.arn
  package_type  = "Image"
  image_uri     = var.image_uri
  architectures = ["x86_64"]
  publish       = true
  memory_size   = var.memory_mb
  timeout       = 29
  image_config {
    command = ["complymate.lambda_handlers.api_handler"]
  }
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
  tracing_config {
    mode = "Active"
  }
  environment {
    variables = merge(var.environment, { RUN_MODE = "api", SERVICE_NAME = "${var.name}-api" })
  }
  depends_on = [aws_cloudwatch_log_group.api]
}

resource "aws_lambda_provisioned_concurrency_config" "api" {
  count                             = var.provisioned_concurrency > 0 ? 1 : 0
  function_name                     = aws_lambda_alias.api.function_name
  qualifier                         = aws_lambda_alias.api.name
  provisioned_concurrent_executions = var.provisioned_concurrency
}

resource "aws_lambda_alias" "api" {
  name             = "live"
  function_name    = aws_lambda_function.api.function_name
  function_version = aws_lambda_function.api.version
}

# ---------------- HTTP API with Cognito JWT authorizer ----------------
resource "aws_apigatewayv2_api" "http" {
  name          = "${var.name}-http"
  protocol_type = "HTTP"
  cors_configuration {
    allow_origins     = var.cors_origins
    allow_methods     = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    allow_headers     = ["authorization", "content-type", "x-tenant-id", "x-request-id", "x-impersonation-id", "x-break-glass-reason", "x-api-key"]
    expose_headers    = ["x-request-id", "content-disposition"]
    allow_credentials = true
    max_age           = 600
  }
}

resource "aws_apigatewayv2_authorizer" "jwt" {
  api_id           = aws_apigatewayv2_api.http.id
  name             = "cognito"
  authorizer_type  = "JWT"
  identity_sources = ["$request.header.Authorization"]
  jwt_configuration {
    issuer   = var.jwt_issuer
    audience = var.jwt_audiences
  }
}

resource "aws_apigatewayv2_integration" "api" {
  api_id                 = aws_apigatewayv2_api.http.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_alias.api.invoke_arn
  payload_format_version = "2.0"
  timeout_milliseconds   = 29000
}

# Every route needs a Cognito JWT except health, the Stripe webhook, the public sign-up check and /m2m (API keys).
resource "aws_apigatewayv2_route" "protected" {
  api_id             = aws_apigatewayv2_api.http.id
  route_key          = "ANY /{proxy+}"
  target             = "integrations/${aws_apigatewayv2_integration.api.id}"
  authorization_type = "JWT"
  authorizer_id      = aws_apigatewayv2_authorizer.jwt.id
}

resource "aws_apigatewayv2_route" "public" {
  for_each  = toset(["GET /health", "GET /health/ready", "POST /webhooks/stripe", "GET /tenants/designated-services", "POST /tenants/check-applicability", "ANY /m2m/{proxy+}"])
  api_id    = aws_apigatewayv2_api.http.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.api.id}"
}

resource "aws_cloudwatch_log_group" "access" {
  name              = "/aws/apigateway/${var.name}-http"
  retention_in_days = var.log_retention_days
  kms_key_id        = var.logs_kms_key_arn
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.http.id
  name        = "$default"
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit   = var.throttle_burst
    throttling_rate_limit    = var.throttle_rate
    detailed_metrics_enabled = true
  }
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.access.arn
    format = jsonencode({
      requestId = "$context.requestId", ip = "$context.identity.sourceIp", routeKey = "$context.routeKey",
      status    = "$context.status", latency = "$context.responseLatency", integrationLatency = "$context.integrationLatency",
      authError = "$context.authorizer.error"
    })
  }
}

resource "aws_lambda_permission" "http" {
  statement_id  = "AllowHttpApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.api.function_name
  qualifier     = aws_lambda_alias.api.name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.http.execution_arn}/*/*"
}
