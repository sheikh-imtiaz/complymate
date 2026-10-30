terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

resource "aws_scheduler_schedule_group" "this" {
  name = var.name
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["scheduler.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "scheduler" {
  name               = "${var.name}-scheduler"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "scheduler" {
  statement {
    actions   = ["sqs:SendMessage"]
    resources = values(var.queue_arns)
  }
  statement {
    actions   = ["kms:GenerateDataKey", "kms:Decrypt"]
    resources = [var.kms_key_arn]
  }
}

resource "aws_iam_role_policy" "scheduler" {
  role   = aws_iam_role.scheduler.id
  policy = data.aws_iam_policy_document.scheduler.json
}

locals {
  # Mirrors complymate.workers.entry.DEFAULT_SCHEDULES. Times are Australia/Sydney.
  schedules = {
    "refresh-watchlists"   = { expr = "cron(0 1 * * ? *)", task = "refresh_watchlists", queue = "screening" }
    "nightly-rescreen"     = { expr = "cron(0 2 * * ? *)", task = "nightly_rescreen", queue = "screening" }
    "verify-audit-chain"   = { expr = "cron(30 2 * * ? *)", task = "verify_audit_chain", queue = "audit" }
    "archive-audit-events" = { expr = "rate(15 minutes)", task = "archive_audit_events", queue = "audit" }
    "send-reminders"       = { expr = "cron(0 7 * * ? *)", task = "send_reminders", queue = "notifications" }
  }
}

resource "aws_scheduler_schedule" "jobs" {
  for_each                     = local.schedules
  name                         = each.key
  group_name                   = aws_scheduler_schedule_group.this.name
  schedule_expression          = each.value.expr
  schedule_expression_timezone = "Australia/Sydney"
  flexible_time_window {
    mode                      = "FLEXIBLE"
    maximum_window_in_minutes = 10
  }
  target {
    arn      = var.queue_arns[each.value.queue]
    role_arn = aws_iam_role.scheduler.arn
    input    = jsonencode({ task = each.value.task, payload = {} })
    retry_policy {
      maximum_retry_attempts = 3
    }
  }
}
