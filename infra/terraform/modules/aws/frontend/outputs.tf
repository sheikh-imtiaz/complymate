output "default_domains" { value = { for k, a in aws_amplify_app.this : k => "https://${var.branch}.${a.default_domain}" } }
output "app_ids" { value = { for k, a in aws_amplify_app.this : k => a.id } }
