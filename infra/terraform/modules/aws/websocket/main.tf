terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

data "aws_region" "current" {}

# API Gateway WebSocket for "Ask the Rules" streaming. Same image, ws_handler entrypoint.
resource "aws_apigatewayv2_api" "ws" {
  name                       = "${var.name}-ws"
  protocol_type              = "WEBSOCKET"
  route_selection_expression = "$request.body.action"
}

resource "aws_cloudwatch_log_group" "ws" {
  name              = "/aws/lambda/${var.name}-ws"
  retention_in_days = var.log_retention_days
}

locals {
  management_endpoint = "https://${aws_apigatewayv2_api.ws.id}.execute-api.${data.aws_region.current.name}.amazonaws.com/${var.stage_name}"
}

resource "aws_lambda_function" "ws" {
  function_name = "${var.name}-ws"
  role          = var.role_arn
  package_type  = "Image"
  image_uri     = var.image_uri
  memory_size   = 1536
  timeout       = 120
  image_config {
    command = ["complymate.lambda_handlers.ws_handler"]
  }
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
  tracing_config {
    mode = "Active"
  }
  environment {
    variables = merge(var.environment, { RUN_MODE = "api", SERVICE_NAME = "${var.name}-ws", WS_API_ENDPOINT = local.management_endpoint })
  }
  depends_on = [aws_cloudwatch_log_group.ws]
}

resource "aws_apigatewayv2_integration" "ws" {
  api_id             = aws_apigatewayv2_api.ws.id
  integration_type   = "AWS_PROXY"
  integration_uri    = aws_lambda_function.ws.invoke_arn
  integration_method = "POST"
}

resource "aws_apigatewayv2_route" "routes" {
  for_each  = toset(["$connect", "$disconnect", "$default", "chat", "ping"])
  api_id    = aws_apigatewayv2_api.ws.id
  route_key = each.value
  target    = "integrations/${aws_apigatewayv2_integration.ws.id}"
}

resource "aws_apigatewayv2_stage" "ws" {
  api_id      = aws_apigatewayv2_api.ws.id
  name        = var.stage_name
  auto_deploy = true
  default_route_settings {
    throttling_burst_limit = 50
    throttling_rate_limit  = 20
  }
}

resource "aws_lambda_permission" "ws" {
  statement_id  = "AllowWebSocketApi"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ws.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.ws.execution_arn}/*/*"
}
