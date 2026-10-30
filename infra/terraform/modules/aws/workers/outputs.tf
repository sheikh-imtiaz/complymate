output "function_name" { value = aws_lambda_function.worker.function_name }
output "function_arn" { value = aws_lambda_function.worker.arn }
output "queue_arns" { value = { for k, q in aws_sqs_queue.this : k => q.arn } }
output "queue_urls" { value = { for k, q in aws_sqs_queue.this : k => q.url } }
output "dlq_names" { value = { for k, q in aws_sqs_queue.dlq : k => q.name } }
output "queue_names" { value = { for k, q in aws_sqs_queue.this : k => q.name } }
