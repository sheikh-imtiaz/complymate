output "ws_url" { value = "${aws_apigatewayv2_api.ws.api_endpoint}/${var.stage_name}" }
output "api_id" { value = aws_apigatewayv2_api.ws.id }
output "management_endpoint" { value = local.management_endpoint }
output "function_name" { value = aws_lambda_function.ws.function_name }
