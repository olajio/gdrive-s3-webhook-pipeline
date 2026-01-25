# Data source for Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda"
  output_path = "${path.module}/lambda_package.zip"
}

# Webhook handler Lambda function
resource "aws_lambda_function" "webhook_handler" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-webhook-handler-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "webhook_handler.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = var.webhook_handler_timeout
  memory_size     = var.webhook_handler_memory

  environment {
    variables = {
      S3_BUCKET           = aws_s3_bucket.gdrive_sync.id
      S3_PREFIX           = "gdrive/"
      CHANNELS_TABLE      = aws_dynamodb_table.gdrive_channels.name
      SYNC_LOG_TABLE      = aws_dynamodb_table.gdrive_s3_sync_log.name
      SNS_TOPIC_ARN       = aws_sns_topic.alerts.arn
      ALLOWED_EXTENSIONS  = var.allowed_extensions
      MAX_FILE_SIZE_MB    = var.max_file_size_mb
      ENVIRONMENT         = var.environment
    }
  }

  # Increase reserved concurrent executions for production
  reserved_concurrent_executions = var.environment == "prod" ? 100 : -1

  # Enable active tracing with X-Ray
  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.webhook_handler
  ]
}

# Channel renewal Lambda function
resource "aws_lambda_function" "channel_renewal" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "${var.project_name}-channel-renewal-${var.environment}"
  role            = aws_iam_role.lambda_execution.arn
  handler         = "channel_renewal.lambda_handler"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  runtime         = "python3.11"
  timeout         = var.channel_renewal_timeout
  memory_size     = var.channel_renewal_memory

  environment {
    variables = {
      CHANNELS_TABLE     = aws_dynamodb_table.gdrive_channels.name
      SNS_TOPIC_ARN      = aws_sns_topic.alerts.arn
      WEBHOOK_ENDPOINT   = "${aws_apigatewayv2_stage.webhook.invoke_url}/webhook"
      GDRIVE_FOLDER_ID   = var.gdrive_folder_id
      ENVIRONMENT        = var.environment
    }
  }

  # Enable active tracing with X-Ray
  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.channel_renewal
  ]
}

# CloudWatch log group for webhook handler
resource "aws_cloudwatch_log_group" "webhook_handler" {
  name              = "/aws/lambda/${var.project_name}-webhook-handler-${var.environment}"
  retention_in_days = var.log_retention_days
}

# CloudWatch log group for channel renewal
resource "aws_cloudwatch_log_group" "channel_renewal" {
  name              = "/aws/lambda/${var.project_name}-channel-renewal-${var.environment}"
  retention_in_days = var.log_retention_days
}

# Lambda permission for API Gateway to invoke webhook handler
resource "aws_lambda_permission" "api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.webhook.execution_arn}/*/*"
}

# EventBridge (CloudWatch Events) rule for channel renewal
resource "aws_cloudwatch_event_rule" "channel_renewal" {
  name                = "${var.project_name}-channel-renewal-${var.environment}"
  description         = "Trigger channel renewal Lambda every 12 hours"
  schedule_expression = "rate(12 hours)"
}

resource "aws_cloudwatch_event_target" "channel_renewal" {
  rule      = aws_cloudwatch_event_rule.channel_renewal.name
  target_id = "ChannelRenewalLambda"
  arn       = aws_lambda_function.channel_renewal.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.channel_renewal.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.channel_renewal.arn
}
