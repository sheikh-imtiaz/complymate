output "group_name" { value = aws_scheduler_schedule_group.this.name }
output "role_arn" { value = aws_iam_role.scheduler.arn }
