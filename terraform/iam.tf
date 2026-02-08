# ==================================================
# Customer Care Call Processing System - IAM Roles & Policies
# ==================================================

# Lambda execution role
resource "aws_iam_role" "lambda_execution" {
  name = "${var.project_name}-lambda-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

# Lambda basic execution policy (CloudWatch Logs)
resource "aws_iam_role_policy_attachment" "lambda_basic_execution" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# X-Ray tracing policy
resource "aws_iam_role_policy_attachment" "lambda_xray" {
  role       = aws_iam_role.lambda_execution.name
  policy_arn = "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess"
}

# Custom policy for Lambda functions
resource "aws_iam_role_policy" "lambda_custom" {
  name = "${var.project_name}-lambda-policy-${var.environment}"
  role = aws_iam_role.lambda_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # S3 permissions
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:HeadObject",
          "s3:DeleteObject"
        ]
        Resource = "${aws_s3_bucket.call_storage.arn}/*"
      },
      {
        Effect = "Allow"
        Action = [
          "s3:ListBucket"
        ]
        Resource = aws_s3_bucket.call_storage.arn
      },
      # DynamoDB permissions
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = [
          aws_dynamodb_table.call_summaries.arn,
          "${aws_dynamodb_table.call_summaries.arn}/index/*",
          aws_dynamodb_table.websocket_connections.arn,
          "${aws_dynamodb_table.websocket_connections.arn}/index/*",
          aws_dynamodb_table.webhook_channels.arn,
          "${aws_dynamodb_table.webhook_channels.arn}/index/*"
        ]
      },
      # Secrets Manager permissions
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:*:secret:${var.google_credentials_secret_name}*"
        ]
      },
      # Amazon Transcribe permissions
      {
        Effect = "Allow"
        Action = [
          "transcribe:StartTranscriptionJob",
          "transcribe:GetTranscriptionJob",
          "transcribe:ListTranscriptionJobs"
        ]
        Resource = "*"
      },
      # Amazon Bedrock permissions
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel",
          "bedrock:InvokeModelWithResponseStream"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-*"
        ]
      },
      # Step Functions permissions
      {
        Effect = "Allow"
        Action = [
          "states:StartExecution"
        ]
        Resource = aws_sfn_state_machine.call_processing.arn
      },
      # API Gateway Management API (for WebSocket)
      {
        Effect = "Allow"
        Action = [
          "execute-api:ManageConnections"
        ]
        Resource = "${aws_apigatewayv2_api.websocket.execution_arn}/*"
      },
      # SNS permissions for alerts
      {
        Effect = "Allow"
        Action = [
          "sns:Publish"
        ]
        Resource = aws_sns_topic.alerts.arn
      },
      # CloudWatch Metrics
      {
        Effect = "Allow"
        Action = [
          "cloudwatch:PutMetricData"
        ]
        Resource = "*"
      },
      # CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-*"
      }
    ]
  })
}

# API Gateway execution role (for CloudWatch logging)
resource "aws_iam_role" "api_gateway_cloudwatch" {
  count = var.enable_api_gateway_logging ? 1 : 0
  name  = "${var.project_name}-apigw-cloudwatch-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "apigateway.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "api_gateway_cloudwatch" {
  count      = var.enable_api_gateway_logging ? 1 : 0
  role       = aws_iam_role.api_gateway_cloudwatch[0].name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
}

# --------------------------------------------------
# Deployer IAM User + Group (for AWS CLI/Terraform)
# --------------------------------------------------

resource "aws_iam_policy" "deployer_policy" {
  name        = "${var.project_name}-deployer-policy-${var.environment}"
  description = "Permissions for deploying and operating the customer-care-call-processor infrastructure"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "iam:*",
          "s3:*",
          "dynamodb:*",
          "lambda:*",
          "apigateway:*",
          "apigatewayv2:*",
          "cognito-idp:*",
          "logs:*",
          "cloudwatch:*",
          "sns:*",
          "secretsmanager:*",
          "states:*",
          "events:*",
          "xray:*",
          "tag:*",
          "resource-groups:*",
          "bedrock:*",
          "transcribe:*",
          "sts:GetCallerIdentity"
        ]
        Resource = "*"
      }
    ]
  })

  tags = var.tags
}

resource "aws_iam_group" "deployer" {
  name = var.deployer_group_name
  tags = var.tags
}

resource "aws_iam_user" "deployer" {
  name = var.deployer_user_name
  tags = var.tags
}

resource "aws_iam_group_policy_attachment" "deployer_policy" {
  group      = aws_iam_group.deployer.name
  policy_arn = aws_iam_policy.deployer_policy.arn
}

resource "aws_iam_user_group_membership" "deployer_membership" {
  user   = aws_iam_user.deployer.name
  groups = [aws_iam_group.deployer.name]
}

resource "aws_iam_access_key" "deployer" {
  user = aws_iam_user.deployer.name
}
