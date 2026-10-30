output "cluster_endpoint" { value = aws_rds_cluster.this.endpoint }
output "proxy_endpoint" { value = aws_db_proxy.this.endpoint }
output "app_secret_arn" { value = aws_secretsmanager_secret.app.arn }
output "master_secret_arn" { value = aws_rds_cluster.this.master_user_secret[0].secret_arn }
output "security_group_id" { value = aws_security_group.db.id }
output "cluster_arn" { value = aws_rds_cluster.this.arn }
output "cluster_id" { value = aws_rds_cluster.this.id }
