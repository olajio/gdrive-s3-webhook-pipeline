# ==================================================
# Customer Care Call Processing System - Lambda Functions
# ==================================================

# -------------------------
# Lambda Layer for shared dependencies
# -------------------------

data "archive_file" "lambda_layer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda"
  output_path = "${path.module}/lambda_layer.zip"
}

resource "aws_lambda_layer_version" "dependencies" {
  filename            = data.archive_file.lambda_layer_zip.output_path
  layer_name          = "${var.project_name}-dependencies-${var.environment}"
  source_code_hash    = data.archive_file.lambda_layer_zip.output_base64sha256
  compatible_runtimes = ["python3.11"]
  description         = "Shared dependencies for call processing lambdas"
}

# -------------------------
# Webhook Handler Lambda
# -------------------------

data "archive_file" "webhook_handler_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src/lambda/webhook"
  output_path = "${path.module}/webhook_handler.zip"
}

resource "aws_lambda_function" "webhook_handler" {
  filename         = data.archive_file.webhook_handler_zip.output_path
  function_name    = "${var.project_name}-webhook-handler-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "handler.handler"
  source_code_hash = data.archive_file.webhook_handler_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.webhook_handler_timeout
  memory_size      = var.webhook_handler_memory
  layers           = [aws_lambda_layer_version.dependencies.arn]

  environment {
    variables = {
      S3_BUCKET                 = aws_s3_bucket.call_storage.id
      DYNAMODB_TABLE            = aws_dynamodb_table.call_summaries.name
      STEP_FUNCTION_ARN         = aws_sfn_state_machine.call_processing.arn
      GOOGLE_CREDENTIALS_SECRET = var.google_credentials_secret_name
      GDRIVE_FOLDER_ID          = var.gdrive_folder_id
      ENVIRONMENT               = var.environment
    }
  }

  reserved_concurrent_executions = var.environment == "prod" ? 100 : -1

  tracing_config {
    mode = "Active"
  }

  depends_on = [
    aws_iam_role_policy_attachment.lambda_basic_execution,
    aws_cloudwatch_log_group.webhook_handler
  ]
}

# -------------------------
# Processing Lambda Functions
# -------------------------

# Start Transcribe Lambda
data "archive_file" "start_transcribe_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/processing/start_transcribe.py"
  output_path = "${path.module}/start_transcribe.zip"
}

resource "aws_lambda_function" "start_transcribe" {
  filename         = data.archive_file.start_transcribe_zip.output_path
  function_name    = "${var.project_name}-start-transcribe-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "start_transcribe.handler"
  source_code_hash = data.archive_file.start_transcribe_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      TRANSCRIBE_OUTPUT_BUCKET = aws_s3_bucket.call_storage.id
      DYNAMODB_TABLE           = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT              = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# Process Transcript Lambda
data "archive_file" "process_transcript_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/processing/process_transcript.py"
  output_path = "${path.module}/process_transcript.zip"
}

resource "aws_lambda_function" "process_transcript" {
  filename         = data.archive_file.process_transcript_zip.output_path
  function_name    = "${var.project_name}-process-transcript-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "process_transcript.handler"
  source_code_hash = data.archive_file.process_transcript_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.processing_lambda_timeout
  memory_size      = var.processing_lambda_memory

  environment {
    variables = {
      S3_BUCKET      = aws_s3_bucket.call_storage.id
      DYNAMODB_TABLE = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# Generate Summary Lambda (Bedrock)
data "archive_file" "generate_summary_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/processing/generate_summary.py"
  output_path = "${path.module}/generate_summary.zip"
}

resource "aws_lambda_function" "generate_summary" {
  filename         = data.archive_file.generate_summary_zip.output_path
  function_name    = "${var.project_name}-generate-summary-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "generate_summary.handler"
  source_code_hash = data.archive_file.generate_summary_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = var.bedrock_lambda_timeout
  memory_size      = var.bedrock_lambda_memory

  environment {
    variables = {
      BEDROCK_MODEL_ID = var.bedrock_model_id
      MAX_TOKENS       = var.bedrock_max_tokens
      DYNAMODB_TABLE   = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT      = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# Save Summary Lambda
data "archive_file" "save_summary_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/processing/save_summary.py"
  output_path = "${path.module}/save_summary.zip"
}

resource "aws_lambda_function" "save_summary" {
  filename         = data.archive_file.save_summary_zip.output_path
  function_name    = "${var.project_name}-save-summary-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "save_summary.handler"
  source_code_hash = data.archive_file.save_summary_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 60
  memory_size      = 256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# Update Status Lambda
data "archive_file" "update_status_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/processing/update_status.py"
  output_path = "${path.module}/update_status.zip"
}

resource "aws_lambda_function" "update_status" {
  filename         = data.archive_file.update_status_zip.output_path
  function_name    = "${var.project_name}-update-status-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "update_status.handler"
  source_code_hash = data.archive_file.update_status_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# -------------------------
# API Lambda Functions
# -------------------------

# List Summaries Lambda
data "archive_file" "list_summaries_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/api/list_summaries.py"
  output_path = "${path.module}/list_summaries.zip"
}

resource "aws_lambda_function" "list_summaries" {
  filename         = data.archive_file.list_summaries_zip.output_path
  function_name    = "${var.project_name}-list-summaries-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "list_summaries.handler"
  source_code_hash = data.archive_file.list_summaries_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.call_summaries.name
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# Get Summary Lambda
data "archive_file" "get_summary_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/api/get_summary.py"
  output_path = "${path.module}/get_summary.zip"
}

resource "aws_lambda_function" "get_summary" {
  filename         = data.archive_file.get_summary_zip.output_path
  function_name    = "${var.project_name}-get-summary-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "get_summary.handler"
  source_code_hash = data.archive_file.get_summary_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.call_summaries.name
      S3_BUCKET      = aws_s3_bucket.call_storage.id
      ENVIRONMENT    = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# -------------------------
# WebSocket Lambda Functions
# -------------------------

# WebSocket Connect Lambda
data "archive_file" "ws_connect_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/websocket/connect.py"
  output_path = "${path.module}/ws_connect.zip"
}

resource "aws_lambda_function" "websocket_connect" {
  filename         = data.archive_file.ws_connect_zip.output_path
  function_name    = "${var.project_name}-ws-connect-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "connect.handler"
  source_code_hash = data.archive_file.ws_connect_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      CONNECTIONS_TABLE = aws_dynamodb_table.websocket_connections.name
      ENVIRONMENT       = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# WebSocket Disconnect Lambda
data "archive_file" "ws_disconnect_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/websocket/disconnect.py"
  output_path = "${path.module}/ws_disconnect.zip"
}

resource "aws_lambda_function" "websocket_disconnect" {
  filename         = data.archive_file.ws_disconnect_zip.output_path
  function_name    = "${var.project_name}-ws-disconnect-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "disconnect.handler"
  source_code_hash = data.archive_file.ws_disconnect_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 10
  memory_size      = 128

  environment {
    variables = {
      CONNECTIONS_TABLE = aws_dynamodb_table.websocket_connections.name
      ENVIRONMENT       = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# WebSocket Notify Lambda
data "archive_file" "ws_notify_zip" {
  type        = "zip"
  source_file = "${path.module}/../src/lambda/websocket/notify.py"
  output_path = "${path.module}/ws_notify.zip"
}

resource "aws_lambda_function" "websocket_notify" {
  filename         = data.archive_file.ws_notify_zip.output_path
  function_name    = "${var.project_name}-ws-notify-${var.environment}"
  role             = aws_iam_role.lambda_execution.arn
  handler          = "notify.handler"
  source_code_hash = data.archive_file.ws_notify_zip.output_base64sha256
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      CONNECTIONS_TABLE  = aws_dynamodb_table.websocket_connections.name
      WEBSOCKET_ENDPOINT = aws_apigatewayv2_stage.websocket.invoke_url
      ENVIRONMENT        = var.environment
    }
  }

  tracing_config {
    mode = "Active"
  }
}

# -------------------------
# CloudWatch Log Groups
# -------------------------

resource "aws_cloudwatch_log_group" "webhook_handler" {
  name              = "/aws/lambda/${var.project_name}-webhook-handler-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "start_transcribe" {
  name              = "/aws/lambda/${var.project_name}-start-transcribe-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "process_transcript" {
  name              = "/aws/lambda/${var.project_name}-process-transcript-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "generate_summary" {
  name              = "/aws/lambda/${var.project_name}-generate-summary-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "save_summary" {
  name              = "/aws/lambda/${var.project_name}-save-summary-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "list_summaries" {
  name              = "/aws/lambda/${var.project_name}-list-summaries-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "get_summary" {
  name              = "/aws/lambda/${var.project_name}-get-summary-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "websocket_connect" {
  name              = "/aws/lambda/${var.project_name}-ws-connect-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "websocket_disconnect" {
  name              = "/aws/lambda/${var.project_name}-ws-disconnect-${var.environment}"
  retention_in_days = var.log_retention_days
}

resource "aws_cloudwatch_log_group" "websocket_notify" {
  name              = "/aws/lambda/${var.project_name}-ws-notify-${var.environment}"
  retention_in_days = var.log_retention_days
}

# -------------------------
# Lambda Permissions
# -------------------------

resource "aws_lambda_permission" "api_gateway_webhook" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.webhook_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_list" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.list_summaries.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rest_api.execution_arn}/*/*"
}

resource "aws_lambda_permission" "api_gateway_get" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.get_summary.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.rest_api.execution_arn}/*/*"
}
