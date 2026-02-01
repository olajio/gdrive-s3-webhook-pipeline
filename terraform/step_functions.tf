# ==================================================
# Customer Care Call Processing System - Step Functions
# ==================================================

# Step Functions State Machine for Call Processing Pipeline
resource "aws_sfn_state_machine" "call_processing" {
  name     = "${var.project_name}-pipeline-${var.environment}"
  role_arn = aws_iam_role.step_functions_role.arn

  definition = templatefile("${path.module}/../stepfunctions/call-processing.asl.json", {
    UpdateStatusFunctionArn      = aws_lambda_function.update_status.arn
    StartTranscribeFunctionArn   = aws_lambda_function.start_transcribe.arn
    ProcessTranscriptFunctionArn = aws_lambda_function.process_transcript.arn
    GenerateSummaryFunctionArn   = aws_lambda_function.generate_summary.arn
    SaveSummaryFunctionArn       = aws_lambda_function.save_summary.arn
    NotifyFunctionArn            = aws_lambda_function.websocket_notify.arn
  })

  logging_configuration {
    log_destination        = "${aws_cloudwatch_log_group.step_functions.arn}:*"
    include_execution_data = true
    level                  = "ALL"
  }

  tracing_configuration {
    enabled = true
  }

  tags = merge(
    var.tags,
    {
      Name = "${var.project_name}-pipeline-${var.environment}"
    }
  )
}

# CloudWatch Log Group for Step Functions
resource "aws_cloudwatch_log_group" "step_functions" {
  name              = "/aws/step-functions/${var.project_name}-pipeline-${var.environment}"
  retention_in_days = var.log_retention_days

  tags = var.tags
}

# IAM Role for Step Functions
resource "aws_iam_role" "step_functions_role" {
  name = "${var.project_name}-sfn-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "states.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Step Functions
resource "aws_iam_role_policy" "step_functions_policy" {
  name = "${var.project_name}-sfn-policy-${var.environment}"
  role = aws_iam_role.step_functions_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = [
          aws_lambda_function.update_status.arn,
          aws_lambda_function.start_transcribe.arn,
          aws_lambda_function.process_transcript.arn,
          aws_lambda_function.generate_summary.arn,
          aws_lambda_function.save_summary.arn,
          aws_lambda_function.websocket_notify.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "transcribe:GetTranscriptionJob"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogDelivery",
          "logs:GetLogDelivery",
          "logs:UpdateLogDelivery",
          "logs:DeleteLogDelivery",
          "logs:ListLogDeliveries",
          "logs:PutResourcePolicy",
          "logs:DescribeResourcePolicies",
          "logs:DescribeLogGroups"
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets"
        ]
        Resource = "*"
      }
    ]
  })
}

# EventBridge rule to trigger Step Functions on Transcribe completion
resource "aws_cloudwatch_event_rule" "transcribe_complete" {
  name        = "${var.project_name}-transcribe-complete-${var.environment}"
  description = "Trigger when Amazon Transcribe job completes"

  event_pattern = jsonencode({
    source      = ["aws.transcribe"]
    detail-type = ["Transcribe Job State Change"]
    detail = {
      TranscriptionJobStatus = ["COMPLETED", "FAILED"]
    }
  })

  tags = var.tags
}
