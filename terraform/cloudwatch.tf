# =================================================================
# CloudWatch Monitoring Configuration
# Customer Care Call Processing System
# =================================================================

# SNS topic for alerts
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-alerts-${var.environment}"

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-alerts-${var.environment}"
    }
  )
}

# Email subscription for alerts
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# =================================================================
# CloudWatch Dashboard
# =================================================================

resource "aws_cloudwatch_dashboard" "call_processing" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      # Row 1: Pipeline Overview
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 1
        properties = {
          markdown = "# Customer Care Call Processing Pipeline - ${var.environment}"
        }
      },

      # Row 2: Call Processing Metrics
      {
        type   = "metric"
        x      = 0
        y      = 1
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CallProcessing", "CallsReceived", { stat = "Sum", label = "Calls Received" }],
            [".", "CallsCompleted", { stat = "Sum", label = "Calls Completed" }],
            [".", "CallsFailed", { stat = "Sum", label = "Calls Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Call Processing Volume"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 1
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CallProcessing", "TranscriptionTime", { stat = "Average", label = "Avg Transcription" }],
            [".", "SummarizationTime", { stat = "Average", label = "Avg Summarization" }],
            [".", "TotalProcessingTime", { stat = "Average", label = "Avg Total Time" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Processing Time (seconds)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 1
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["CallProcessing", "SuccessRate", { stat = "Average", label = "Success Rate %" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Success Rate"
          yAxis = {
            left = { min = 0, max = 100 }
          }
        }
      },

      # Row 3: Lambda Performance
      {
        type   = "metric"
        x      = 0
        y      = 7
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", aws_lambda_function.webhook_handler.function_name, { label = "Webhook Handler" }],
            ["...", aws_lambda_function.start_transcribe.function_name, { label = "Start Transcribe" }],
            ["...", aws_lambda_function.process_transcript.function_name, { label = "Process Transcript" }],
            ["...", aws_lambda_function.generate_summary.function_name, { label = "Generate Summary" }],
            ["...", aws_lambda_function.save_summary.function_name, { label = "Save Summary" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Invocations by Function"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 7
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", aws_lambda_function.webhook_handler.function_name, { stat = "Average", label = "Webhook Handler" }],
            ["...", aws_lambda_function.start_transcribe.function_name, { stat = "Average", label = "Start Transcribe" }],
            ["...", aws_lambda_function.process_transcript.function_name, { stat = "Average", label = "Process Transcript" }],
            ["...", aws_lambda_function.generate_summary.function_name, { stat = "Average", label = "Generate Summary" }],
            ["...", aws_lambda_function.save_summary.function_name, { stat = "Average", label = "Save Summary" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Duration (ms)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },

      # Row 4: Errors
      {
        type   = "metric"
        x      = 0
        y      = 13
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", aws_lambda_function.webhook_handler.function_name, { label = "Webhook Handler" }],
            ["...", aws_lambda_function.start_transcribe.function_name, { label = "Start Transcribe" }],
            ["...", aws_lambda_function.process_transcript.function_name, { label = "Process Transcript" }],
            ["...", aws_lambda_function.generate_summary.function_name, { label = "Generate Summary" }],
            ["...", aws_lambda_function.save_summary.function_name, { label = "Save Summary" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Errors by Function"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 13
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsFailed", "StateMachineArn", aws_sfn_state_machine.call_processing.arn, { label = "Failed Executions" }],
            [".", "ExecutionsTimedOut", ".", ".", { label = "Timed Out" }],
            [".", "ExecutionsAborted", ".", ".", { label = "Aborted" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Step Functions Failures"
          yAxis = {
            left = { min = 0 }
          }
        }
      },

      # Row 5: Step Functions Execution
      {
        type   = "metric"
        x      = 0
        y      = 19
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionsStarted", "StateMachineArn", aws_sfn_state_machine.call_processing.arn, { label = "Started" }],
            [".", "ExecutionsSucceeded", ".", ".", { label = "Succeeded" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Step Functions Executions"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 19
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/States", "ExecutionTime", "StateMachineArn", aws_sfn_state_machine.call_processing.arn, { stat = "Average", label = "Avg Execution Time" }],
            ["...", { stat = "Maximum", label = "Max Execution Time" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Step Functions Execution Time (ms)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },

      # Row 6: API Gateway
      {
        type   = "metric"
        x      = 0
        y      = 25
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.project_name}-api-${var.environment}", { stat = "Sum", label = "API Requests" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API Gateway Requests"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 25
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", "${var.project_name}-api-${var.environment}", { stat = "Average", label = "Avg Latency" }],
            ["...", { stat = "p99", label = "p99 Latency" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "API Gateway Latency (ms)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 25
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "4XXError", "ApiName", "${var.project_name}-api-${var.environment}", { stat = "Sum", label = "4XX Errors" }],
            [".", "5XXError", ".", ".", { stat = "Sum", label = "5XX Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "API Gateway Errors"
          yAxis = {
            left = { min = 0 }
          }
        }
      },

      # Row 7: Transcribe and Bedrock
      {
        type   = "metric"
        x      = 0
        y      = 31
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CallProcessing", "TranscribeJobsStarted", { stat = "Sum", label = "Jobs Started" }],
            [".", "TranscribeJobsCompleted", { stat = "Sum", label = "Jobs Completed" }],
            [".", "TranscribeJobsFailed", { stat = "Sum", label = "Jobs Failed" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Amazon Transcribe Jobs"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 31
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["CallProcessing", "BedrockCalls", { stat = "Sum", label = "Bedrock Calls" }],
            [".", "BedrockErrors", { stat = "Sum", label = "Bedrock Errors" }],
            [".", "BedrockLatency", { stat = "Average", label = "Avg Latency (ms)" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Amazon Bedrock (Claude 3.5)"
          yAxis = {
            left = { min = 0 }
          }
        }
      },

      # Row 8: DynamoDB
      {
        type   = "metric"
        x      = 0
        y      = 37
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", aws_dynamodb_table.call_summaries.name, { stat = "Sum", label = "Read Capacity" }],
            [".", "ConsumedWriteCapacityUnits", ".", ".", { stat = "Sum", label = "Write Capacity" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "DynamoDB Capacity"
          yAxis = {
            left = { min = 0 }
          }
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 37
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", aws_dynamodb_table.call_summaries.name, "Operation", "GetItem", { stat = "Average", label = "GetItem" }],
            ["...", "PutItem", { stat = "Average", label = "PutItem" }],
            ["...", "Query", { stat = "Average", label = "Query" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "DynamoDB Latency (ms)"
          yAxis = {
            left = { min = 0 }
          }
        }
      }
    ]
  })
}

# =================================================================
# CloudWatch Alarms
# =================================================================

# Lambda Error Alarm - Webhook Handler
resource "aws_cloudwatch_metric_alarm" "webhook_handler_errors" {
  alarm_name          = "${var.project_name}-webhook-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Lambda webhook handler errors exceed threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.webhook_handler.function_name
  }

  tags = var.tags
}

# Step Functions Failure Alarm
resource "aws_cloudwatch_metric_alarm" "step_functions_failures" {
  alarm_name          = "${var.project_name}-stepfunctions-failures-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ExecutionsFailed"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Step Functions executions failing"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.call_processing.arn
  }

  tags = var.tags
}

# Bedrock Error Alarm
resource "aws_cloudwatch_metric_alarm" "bedrock_errors" {
  alarm_name          = "${var.project_name}-bedrock-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 3
  alarm_description   = "Bedrock summarization errors"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.generate_summary.function_name
  }

  tags = var.tags
}

# API Gateway 5XX Errors
resource "aws_cloudwatch_metric_alarm" "api_5xx_errors" {
  alarm_name          = "${var.project_name}-api-5xx-errors-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gateway 5XX errors exceed threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  ok_actions          = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-api-${var.environment}"
  }

  tags = var.tags
}

# API Gateway Latency Alarm
resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "${var.project_name}-api-latency-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  extended_statistic  = "p95"
  threshold           = 5000
  alarm_description   = "API Gateway p95 latency exceeds 5 seconds"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    ApiName = "${var.project_name}-api-${var.environment}"
  }

  tags = var.tags
}

# Processing Time Alarm
resource "aws_cloudwatch_metric_alarm" "processing_time" {
  alarm_name          = "${var.project_name}-processing-time-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ExecutionTime"
  namespace           = "AWS/States"
  period              = 300
  statistic           = "Average"
  threshold           = 600000 # 10 minutes in milliseconds
  alarm_description   = "Average call processing time exceeds 10 minutes"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    StateMachineArn = aws_sfn_state_machine.call_processing.arn
  }

  tags = var.tags
}

# DynamoDB Throttling Alarm
resource "aws_cloudwatch_metric_alarm" "dynamodb_throttling" {
  alarm_name          = "${var.project_name}-dynamodb-throttling-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "ThrottledRequests"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "DynamoDB throttling detected"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    TableName = aws_dynamodb_table.call_summaries.name
  }

  tags = var.tags
}

# =================================================================
# CloudWatch Log Groups
# =================================================================

resource "aws_cloudwatch_log_group" "webhook_handler" {
  name              = "/aws/lambda/${var.project_name}-webhook-handler-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "start_transcribe" {
  name              = "/aws/lambda/${var.project_name}-start-transcribe-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "process_transcript" {
  name              = "/aws/lambda/${var.project_name}-process-transcript-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "generate_summary" {
  name              = "/aws/lambda/${var.project_name}-generate-summary-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "save_summary" {
  name              = "/aws/lambda/${var.project_name}-save-summary-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "update_status" {
  name              = "/aws/lambda/${var.project_name}-update-status-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api_list_summaries" {
  name              = "/aws/lambda/${var.project_name}-list-summaries-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api_get_summary" {
  name              = "/aws/lambda/${var.project_name}-get-summary-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api_get_audio_url" {
  name              = "/aws/lambda/${var.project_name}-get-audio-url-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "api_get_transcript" {
  name              = "/aws/lambda/${var.project_name}-get-transcript-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "websocket_connect" {
  name              = "/aws/lambda/${var.project_name}-ws-connect-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "websocket_disconnect" {
  name              = "/aws/lambda/${var.project_name}-ws-disconnect-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "websocket_notify" {
  name              = "/aws/lambda/${var.project_name}-ws-notify-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/states/${var.project_name}-call-processing-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# =================================================================
# CloudWatch Insights Queries (Saved)
# =================================================================

resource "aws_cloudwatch_query_definition" "error_analysis" {
  name = "${var.project_name}/${var.environment}/error-analysis"

  log_group_names = [
    aws_cloudwatch_log_group.webhook_handler.name,
    aws_cloudwatch_log_group.start_transcribe.name,
    aws_cloudwatch_log_group.process_transcript.name,
    aws_cloudwatch_log_group.generate_summary.name,
    aws_cloudwatch_log_group.save_summary.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message, @logStream
    | filter @message like /(?i)(error|exception|failed)/
    | sort @timestamp desc
    | limit 100
  EOT
}

resource "aws_cloudwatch_query_definition" "call_processing_timeline" {
  name = "${var.project_name}/${var.environment}/call-processing-timeline"

  log_group_names = [
    aws_cloudwatch_log_group.webhook_handler.name,
    aws_cloudwatch_log_group.start_transcribe.name,
    aws_cloudwatch_log_group.process_transcript.name,
    aws_cloudwatch_log_group.generate_summary.name,
    aws_cloudwatch_log_group.save_summary.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message
    | filter @message like /call_id/
    | parse @message "call_id=*" as call_id
    | sort @timestamp asc
    | limit 1000
  EOT
}

resource "aws_cloudwatch_query_definition" "bedrock_performance" {
  name = "${var.project_name}/${var.environment}/bedrock-performance"

  log_group_names = [
    aws_cloudwatch_log_group.generate_summary.name
  ]

  query_string = <<-EOT
    fields @timestamp, @message, @duration
    | filter @message like /Bedrock/
    | stats avg(@duration) as avg_duration, max(@duration) as max_duration by bin(1h)
  EOT
}
