terraform {
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.80" }
  }
}

locals {
  # Must match complymate.ports.queue.QueueName. Visibility timeout >= 6x function timeout for batches.
  queues = {
    ocr           = { batch = 5, max_concurrency = 5 }
    screening     = { batch = 10, max_concurrency = 10 }
    exports       = { batch = 1, max_concurrency = 3 }
    notifications = { batch = 10, max_concurrency = 5 }
    audit         = { batch = 1, max_concurrency = 2 }
  }
}

resource "aws_sqs_queue" "dlq" {
  for_each                  = local.queues
  name                      = "${var.name}-${each.key}-dlq"
  message_retention_seconds = 1209600
  kms_master_key_id         = var.kms_key_arn
}

resource "aws_sqs_queue" "this" {
  for_each                   = local.queues
  name                       = "${var.name}-${each.key}"
  visibility_timeout_seconds = var.timeout_seconds * 2
  message_retention_seconds  = 345600
  kms_master_key_id          = var.kms_key_arn
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq[each.key].arn
    maxReceiveCount     = 5
  })
}

resource "aws_cloudwatch_log_group" "worker" {
  name              = "/aws/lambda/${var.name}-worker"
  retention_in_days = var.log_retention_days
}

resource "aws_lambda_function" "worker" {
  function_name = "${var.name}-worker"
  role          = var.role_arn
  package_type  = "Image"
  image_uri     = var.image_uri
  memory_size   = var.memory_mb
  timeout       = var.timeout_seconds
  image_config {
    command = ["complymate.lambda_handlers.worker_handler"]
  }
  vpc_config {
    subnet_ids         = var.subnet_ids
    security_group_ids = var.security_group_ids
  }
  tracing_config {
    mode = "Active"
  }
  ephemeral_storage {
    size = 2048
  }
  environment {
    variables = merge(var.environment, { RUN_MODE = "worker", SERVICE_NAME = "${var.name}-worker", ALEMBIC_INI = "/app/alembic.ini" })
  }
  depends_on = [aws_cloudwatch_log_group.worker]
}

resource "aws_lambda_event_source_mapping" "queues" {
  for_each                           = local.queues
  event_source_arn                   = aws_sqs_queue.this[each.key].arn
  function_name                      = aws_lambda_function.worker.arn
  batch_size                         = each.value.batch
  maximum_batching_window_in_seconds = each.value.batch > 1 ? 5 : 0
  function_response_types            = ["ReportBatchItemFailures"]
  scaling_config {
    maximum_concurrency = max(2, each.value.max_concurrency)
  }
}
