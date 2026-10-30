terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

data "aws_iam_policy_document" "trust" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "sfn" {
  name               = "${var.name}-workflows"
  assume_role_policy = data.aws_iam_policy_document.trust.json
}

data "aws_iam_policy_document" "sfn" {
  statement {
    actions   = ["lambda:InvokeFunction"]
    resources = [var.worker_function_arn, "${var.worker_function_arn}:*"]
  }
  statement {
    actions = ["logs:CreateLogDelivery", "logs:GetLogDelivery", "logs:UpdateLogDelivery", "logs:DeleteLogDelivery",
      "logs:ListLogDeliveries", "logs:PutResourcePolicy", "logs:DescribeResourcePolicies", "logs:DescribeLogGroups",
    "xray:PutTraceSegments", "xray:PutTelemetryRecords", "xray:GetSamplingRules", "xray:GetSamplingTargets"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "sfn" {
  role   = aws_iam_role.sfn.id
  policy = data.aws_iam_policy_document.sfn.json
}

resource "aws_cloudwatch_log_group" "sfn" {
  name              = "/aws/vendedlogs/states/${var.name}"
  retention_in_days = var.log_retention_days
}

locals {
  retry = [{
    ErrorEquals     = ["Lambda.ServiceException", "Lambda.TooManyRequestsException", "Lambda.SdkClientException", "States.TaskFailed"]
    IntervalSeconds = 5
    MaxAttempts     = 3
    BackoffRate     = 2
  }]

  # Program drafting: one agent call per section, max 4 in parallel, then finalize (notify the requester).
  program_draft = {
    Comment = "Draft AML/CTF program sections with the agent"
    StartAt = "DraftSections"
    States = {
      DraftSections = {
        Type           = "Map"
        ItemsPath      = "$.sections"
        MaxConcurrency = 4
        ItemSelector = {
          "task" = "draft_program_section"
          "payload" = {
            "tenant_id.$"    = "$.tenant_id"
            "version_id.$"   = "$.version_id"
            "requested_by.$" = "$.requested_by"
            "section.$"      = "$$.Map.Item.Value"
          }
        }
        ItemProcessor = {
          ProcessorConfig = { Mode = "INLINE" }
          StartAt         = "DraftOne"
          States = {
            DraftOne = {
              Type       = "Task"
              Resource   = "arn:aws:states:::lambda:invoke"
              Parameters = { FunctionName = var.worker_function_arn, "Payload.$" = "$" }
              OutputPath = "$.Payload"
              Retry      = local.retry
              Catch      = [{ ErrorEquals = ["States.ALL"], ResultPath = "$.error", Next = "SectionFailed" }]
              End        = true
            }
            SectionFailed = { Type = "Pass", Result = { status = "failed" }, End = true }
          }
        }
        ResultPath = "$.results"
        Next       = "Finalize"
      }
      Finalize = {
        Type     = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = var.worker_function_arn
          Payload = {
            "task" = "draft_program_finalize"
            "payload" = {
              "tenant_id.$"    = "$.tenant_id"
              "version_id.$"   = "$.version_id"
              "requested_by.$" = "$.requested_by"
              "status"         = "done"
            }
          }
        }
        Retry = local.retry
        End   = true
      }
    }
  }

  regulator_pack = {
    Comment = "Build the regulator pack ZIP"
    StartAt = "Build"
    States = {
      Build = {
        Type       = "Task"
        Resource   = "arn:aws:states:::lambda:invoke"
        Parameters = { FunctionName = var.worker_function_arn, Payload = { "task" = "build_regulator_pack", "payload.$" = "$" } }
        Retry      = local.retry
        End        = true
      }
    }
  }
}

resource "aws_sfn_state_machine" "program_draft" {
  name       = "${var.name}-program-draft"
  role_arn   = aws_iam_role.sfn.arn
  definition = jsonencode(local.program_draft)
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = false
    level                  = "ERROR"
  }
  tracing_configuration {
    enabled = true
  }
}

resource "aws_sfn_state_machine" "regulator_pack" {
  name       = "${var.name}-regulator-pack"
  role_arn   = aws_iam_role.sfn.arn
  definition = jsonencode(local.regulator_pack)
  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.sfn.arn}:*"
    include_execution_data = false
    level                  = "ERROR"
  }
  tracing_configuration {
    enabled = true
  }
}
