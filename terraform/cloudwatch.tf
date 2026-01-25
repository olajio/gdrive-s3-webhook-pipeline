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

# Email subscription (if provided)
resource "aws_sns_topic_subscription" "email_alerts" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# CloudWatch dashboard
resource "aws_cloudwatch_dashboard" "webhook_metrics" {
  dashboard_name = "${var.project_name}-${var.environment}"

  dashboard_body = jsonencode({
    widgets = [
      {
        type = "metric"
        properties = {
          metrics = [
            ["GoogleDriveWebhook", "WebhooksReceived", { stat = "Sum", label = "Webhooks Received" }],
            [".", "FilesUploaded", { stat = "Sum", label = "Files Uploaded" }],
            [".", "FilesSkipped", { stat = "Sum", label = "Files Skipped" }],
            [".", "DuplicateFilesSkipped", { stat = "Sum", label = "Duplicates Skipped" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "File Processing"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["GoogleDriveWebhook", "GoogleDriveErrors", { stat = "Sum", label = "Google Drive Errors" }],
            [".", "AWSErrors", { stat = "Sum", label = "AWS Errors" }],
            [".", "S3UploadErrors", { stat = "Sum", label = "S3 Upload Errors" }],
            [".", "UnexpectedErrors", { stat = "Sum", label = "Unexpected Errors" }],
            [".", "LambdaErrors", { stat = "Sum", label = "Lambda Errors" }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Errors"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", { stat = "Average", label = "Avg Duration" }, { function_name = aws_lambda_function.webhook_handler.function_name }],
            ["...", { stat = "Maximum", label = "Max Duration" }]
          ]
          period = 300
          stat   = "Average"
          region = var.aws_region
          title  = "Lambda Performance"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["GoogleDriveWebhook", "ChannelsCreated", { stat = "Sum", label = "Channels Created" }],
            [".", "ChannelsRenewed", { stat = "Sum", label = "Channels Renewed" }],
            [".", "ChannelCreationErrors", { stat = "Sum", label = "Creation Errors" }],
            [".", "ChannelRenewalErrors", { stat = "Sum", label = "Renewal Errors" }]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "Channel Management"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", { stat = "Sum" }, { function_name = aws_lambda_function.webhook_handler.function_name }],
            [".", "Errors", { stat = "Sum" }, { function_name = aws_lambda_function.webhook_handler.function_name }],
            [".", "Throttles", { stat = "Sum" }, { function_name = aws_lambda_function.webhook_handler.function_name }]
          ]
          period = 300
          stat   = "Sum"
          region = var.aws_region
          title  = "Lambda Invocations"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      },
      {
        type = "metric"
        properties = {
          metrics = [
            ["GoogleDriveWebhook", "BytesUploaded", { stat = "Sum", label = "Bytes Uploaded" }]
          ]
          period = 3600
          stat   = "Sum"
          region = var.aws_region
          title  = "Data Transfer"
          yAxis = {
            left = {
              min = 0
            }
          }
        }
      }
    ]
  })
}

# CloudWatch alarm for high error rate
resource "aws_cloudwatch_metric_alarm" "high_error_rate" {
  alarm_name          = "${var.project_name}-high-error-rate-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "5"
  alarm_description   = "Alert when Lambda error count exceeds threshold"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.webhook_handler.function_name
  }
}

# CloudWatch alarm for channel renewal failures
resource "aws_cloudwatch_metric_alarm" "channel_renewal_failure" {
  alarm_name          = "${var.project_name}-channel-renewal-failure-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "ChannelRenewalErrors"
  namespace           = "GoogleDriveWebhook"
  period              = "3600"
  statistic           = "Sum"
  threshold           = "0"
  alarm_description   = "Alert when channel renewal fails"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

# CloudWatch alarm for Lambda throttling
resource "aws_cloudwatch_metric_alarm" "lambda_throttles" {
  alarm_name          = "${var.project_name}-lambda-throttles-${var.environment}"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "Throttles"
  namespace           = "AWS/Lambda"
  period              = "300"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "Alert when Lambda is being throttled"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    FunctionName = aws_lambda_function.webhook_handler.function_name
  }
}

# CloudWatch log metric filter for invalid webhooks
resource "aws_cloudwatch_log_metric_filter" "invalid_webhooks" {
  name           = "${var.project_name}-invalid-webhooks-${var.environment}"
  log_group_name = aws_cloudwatch_log_group.webhook_handler.name
  pattern        = "Invalid webhook signature"

  metric_transformation {
    name      = "InvalidWebhooks"
    namespace = "GoogleDriveWebhook"
    value     = "1"
  }
}
