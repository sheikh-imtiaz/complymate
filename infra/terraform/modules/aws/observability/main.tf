terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

resource "aws_sns_topic" "alerts" {
  name              = "${var.name}-alerts"
  kms_master_key_id = "alias/aws/sns"
}

resource "aws_sns_topic_subscription" "email" {
  for_each  = toset(var.alert_emails)
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

# Security events: the app logs `security_event` (structlog JSON) → metric → alarm → SNS (security channel).
resource "aws_cloudwatch_log_metric_filter" "security" {
  for_each       = toset(var.app_log_groups)
  name           = "${var.name}-security-${replace(each.value, "/", "-")}"
  log_group_name = each.value
  pattern        = "{ $.event = \"security_event\" }"
  metric_transformation {
    name      = "SecurityEvents"
    namespace = "ComplyMate"
    value     = "1"
  }
}

locals {
  alarms = {
    api-errors = {
      namespace = "AWS/Lambda", metric = "Errors", stat = "Sum", threshold = 5, period = 300,
      dims      = { FunctionName = var.api_function_name }, description = "API Lambda errors"
    }
    worker-errors = {
      namespace = "AWS/Lambda", metric = "Errors", stat = "Sum", threshold = 5, period = 300,
      dims      = { FunctionName = var.worker_function_name }, description = "Worker Lambda errors"
    }
    api-5xx = {
      namespace = "AWS/ApiGateway", metric = "5xx", stat = "Sum", threshold = 10, period = 300,
      dims      = { ApiId = var.http_api_id }, description = "HTTP API 5xx responses"
    }
    audit-chain-break = {
      namespace = "ComplyMate", metric = "AuditChainBreak", stat = "Sum", threshold = 0, period = 300,
      dims      = {}, description = "Audit hash chain verification failed — follow docs/runbooks/audit-chain-break.md"
    }
    screening-job-failed = {
      namespace = "ComplyMate", metric = "ScreeningJobFailed", stat = "Sum", threshold = 0, period = 3600,
      dims      = {}, description = "Sanctions list refresh or nightly re-screening failed"
    }
    security-events = {
      namespace = "ComplyMate", metric = "SecurityEvents", stat = "Sum", threshold = 20, period = 300,
      dims      = {}, description = "Spike in security events (failed logins, exports, role changes)"
    }
    llm-spend = {
      namespace = "ComplyMate", metric = "LLMCostUSD", stat = "Sum", threshold = var.llm_daily_budget_usd, period = 86400,
      dims      = {}, description = "LLM spend over daily budget"
    }
  }
}

resource "aws_cloudwatch_metric_alarm" "this" {
  for_each            = local.alarms
  alarm_name          = "${var.name}-${each.key}"
  alarm_description   = each.value.description
  namespace           = each.value.namespace
  metric_name         = each.value.metric
  statistic           = each.value.stat
  period              = each.value.period
  evaluation_periods  = 1
  threshold           = each.value.threshold
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = each.value.dims
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_p95" {
  alarm_name          = "${var.name}-api-p95-latency"
  alarm_description   = "API p95 latency over 400 ms (non-AI target)"
  namespace           = "AWS/Lambda"
  metric_name         = "Duration"
  extended_statistic  = "p95"
  period              = 300
  evaluation_periods  = 3
  threshold           = 400
  comparison_operator = "GreaterThanThreshold"
  treat_missing_data  = "notBreaching"
  dimensions          = { FunctionName = var.api_function_name }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "dlq" {
  for_each            = var.dlq_names
  alarm_name          = "${var.name}-dlq-${each.key}"
  alarm_description   = "Messages in the ${each.key} dead-letter queue"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateNumberOfMessagesVisible"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 1
  threshold           = 0
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { QueueName = each.value }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "queue_backlog" {
  for_each            = var.queue_names
  alarm_name          = "${var.name}-backlog-${each.key}"
  alarm_description   = "Oldest message in ${each.key} older than 15 minutes"
  namespace           = "AWS/SQS"
  metric_name         = "ApproximateAgeOfOldestMessage"
  statistic           = "Maximum"
  period              = 300
  evaluation_periods  = 3
  threshold           = 900
  comparison_operator = "GreaterThanThreshold"
  dimensions          = { QueueName = each.value }
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_dashboard" "this" {
  dashboard_name = var.name
  dashboard_body = jsonencode({
    widgets = [
      { type = "metric", x = 0, y = 0, width = 12, height = 6, properties = {
        title = "API latency (p50/p95)", region = var.region, stat = "p95",
        metrics = [["AWS/Lambda", "Duration", "FunctionName", var.api_function_name, { stat = "p50" }],
        ["AWS/Lambda", "Duration", "FunctionName", var.api_function_name, { stat = "p95" }]]
      } },
      { type = "metric", x = 12, y = 0, width = 12, height = 6, properties = {
        title = "Errors", region = var.region, stat = "Sum",
        metrics = [["AWS/Lambda", "Errors", "FunctionName", var.api_function_name],
        ["AWS/Lambda", "Errors", "FunctionName", var.worker_function_name]]
      } },
      { type = "metric", x = 0, y = 6, width = 12, height = 6, properties = {
        title   = "Queue depth", region = var.region, stat = "Maximum",
        metrics = [for k, q in var.queue_names : ["AWS/SQS", "ApproximateNumberOfMessagesVisible", "QueueName", q]]
      } },
      { type = "metric", x = 12, y = 6, width = 12, height = 6, properties = {
        title   = "LLM spend (USD) and security events", region = var.region, stat = "Sum",
        metrics = [["ComplyMate", "LLMCostUSD"], ["ComplyMate", "SecurityEvents"]]
      } },
    ]
  })
}
