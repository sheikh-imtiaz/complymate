output "role_arn" { value = aws_iam_role.app.arn }
output "role_name" { value = aws_iam_role.app.name }
output "function_name" { value = aws_lambda_function.api.function_name }
output "http_api_id" { value = aws_apigatewayv2_api.http.id }
output "http_api_endpoint" { value = aws_apigatewayv2_api.http.api_endpoint }
output "http_api_domain" { value = replace(aws_apigatewayv2_api.http.api_endpoint, "https://", "") }
